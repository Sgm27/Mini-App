"""
Setup AWS Infrastructure for Lambda + EFS + RDS (same VPC).

Creates:
  1. IAM Role for Lambda (VPC + EFS permissions)
  2. VPC + 2 public subnets (2 AZs) + Internet Gateway + Route Table
  3. Security Groups: Lambda, EFS, RDS
  4. EFS file system + Access Point + Mount Targets
  5. RDS MySQL (Publicly Accessible for external dev access)
  6. Updates .env with all infrastructure config

Usage:
    python setup_infra.py

Architecture:
    Internet
      ├── Your IP ──→ RDS MySQL (public subnet, Publicly Accessible=Yes)
      └── Lambda Function URL
            │ (public subnet)
            ├──→ RDS MySQL (same VPC, via SG)
            └──→ EFS mount at /mnt/efs
"""

import json
import os
import sys
import time
from typing import Optional

import boto3
from dotenv import load_dotenv

load_dotenv(override=True)

REGION = "ap-southeast-1"
PROJECT_TAG = "mini-app-lambda"

# RDS Configuration
RDS_INSTANCE_ID = "mini-app-db"
RDS_DB_NAME = "miniapp"
RDS_MASTER_USER = "admin"
RDS_MASTER_PASSWORD = "sonktx12345"
RDS_INSTANCE_CLASS = "db.t3.micro"

# EFS Configuration
EFS_MOUNT_PATH = "/mnt/efs"

# IAM Role Configuration
ROLE_NAME = "lambda-basic-execution-role"
TRUST_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }
    ],
}
REQUIRED_POLICIES = [
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole",
    "arn:aws:iam::aws:policy/AmazonElasticFileSystemClientReadWriteAccess",
]
REMOVE_POLICIES = [
    "arn:aws:iam::aws:policy/AmazonS3FullAccess",
]

# Output file
OUTPUT_FILE = "infra_config.json"


def get_session() -> boto3.Session:
    return boto3.Session(
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=REGION,
    )


def log(step: int, total: int, msg: str):
    print(f"  [{step}/{total}] {msg}")


# ─────────────────────────────────────────────
# Step 1: IAM Role
# ─────────────────────────────────────────────
def setup_iam_role(session) -> dict:
    """Create/update IAM role with VPC + EFS permissions, remove old S3 policy."""
    iam = session.client("iam")

    created = False
    try:
        resp = iam.get_role(RoleName=ROLE_NAME)
        role_arn = resp["Role"]["Arn"]
        print(f"  Role already exists: {role_arn}")
    except iam.exceptions.NoSuchEntityException:
        resp = iam.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(TRUST_POLICY),
            Description="Lambda execution role with VPC + EFS access",
        )
        role_arn = resp["Role"]["Arn"]
        created = True
        print(f"  Created role: {role_arn}")
        print("  Waiting 10s for IAM propagation...")
        time.sleep(10)

    # Detach old policies
    attached = {
        p["PolicyArn"]
        for p in iam.list_attached_role_policies(RoleName=ROLE_NAME)["AttachedPolicies"]
    }
    for policy_arn in REMOVE_POLICIES:
        if policy_arn in attached:
            iam.detach_role_policy(RoleName=ROLE_NAME, PolicyArn=policy_arn)
            print(f"  Detached: {policy_arn}")

    # Attach required policies
    attached = {
        p["PolicyArn"]
        for p in iam.list_attached_role_policies(RoleName=ROLE_NAME)["AttachedPolicies"]
    }
    for policy_arn in REQUIRED_POLICIES:
        if policy_arn not in attached:
            iam.attach_role_policy(RoleName=ROLE_NAME, PolicyArn=policy_arn)
            print(f"  Attached: {policy_arn}")
        else:
            print(f"  Already attached: {policy_arn}")

    return {"role_arn": role_arn, "role_created": created}


# ─────────────────────────────────────────────
# Step 2: VPC + Subnets + Internet Gateway
# ─────────────────────────────────────────────
def setup_vpc(ec2) -> dict:
    """Create VPC with 2 public subnets in different AZs."""

    # Check if VPC already exists
    existing = ec2.describe_vpcs(
        Filters=[{"Name": "tag:Project", "Values": [PROJECT_TAG]}]
    )["Vpcs"]
    if existing:
        vpc_id = existing[0]["VpcId"]
        print(f"  VPC already exists: {vpc_id}")

        # Get existing subnets
        subnets = ec2.describe_subnets(
            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
        )["Subnets"]
        subnet_ids = [s["SubnetId"] for s in subnets]

        # Get existing IGW
        igws = ec2.describe_internet_gateways(
            Filters=[{"Name": "attachment.vpc-id", "Values": [vpc_id]}]
        )["InternetGateways"]
        igw_id = igws[0]["InternetGatewayId"] if igws else None

        return {"vpc_id": vpc_id, "subnet_ids": subnet_ids, "igw_id": igw_id}

    # Create VPC
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]
    ec2.create_tags(
        Resources=[vpc_id],
        Tags=[
            {"Key": "Name", "Value": f"{PROJECT_TAG}-vpc"},
            {"Key": "Project", "Value": PROJECT_TAG},
        ],
    )
    # Enable DNS hostname support (required for RDS public access)
    ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={"Value": True})
    ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={"Value": True})
    print(f"  Created VPC: {vpc_id}")

    # Get available AZs
    azs = ec2.describe_availability_zones(
        Filters=[{"Name": "state", "Values": ["available"]}]
    )["AvailabilityZones"]
    az_names = [az["ZoneName"] for az in azs[:2]]

    # Create 2 public subnets
    subnet_ids = []
    for i, az in enumerate(az_names):
        cidr = f"10.0.{i + 1}.0/24"
        subnet = ec2.create_subnet(VpcId=vpc_id, CidrBlock=cidr, AvailabilityZone=az)
        subnet_id = subnet["Subnet"]["SubnetId"]
        ec2.create_tags(
            Resources=[subnet_id],
            Tags=[
                {"Key": "Name", "Value": f"{PROJECT_TAG}-subnet-{i + 1}"},
                {"Key": "Project", "Value": PROJECT_TAG},
            ],
        )
        # Enable auto-assign public IP (needed for RDS public access)
        ec2.modify_subnet_attribute(
            SubnetId=subnet_id, MapPublicIpOnLaunch={"Value": True}
        )
        subnet_ids.append(subnet_id)
        print(f"  Created subnet: {subnet_id} ({az}, {cidr})")

    # Create Internet Gateway
    igw = ec2.create_internet_gateway()
    igw_id = igw["InternetGateway"]["InternetGatewayId"]
    ec2.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
    ec2.create_tags(
        Resources=[igw_id],
        Tags=[
            {"Key": "Name", "Value": f"{PROJECT_TAG}-igw"},
            {"Key": "Project", "Value": PROJECT_TAG},
        ],
    )
    print(f"  Created IGW: {igw_id}")

    # Create Route Table with route to IGW
    rtb = ec2.create_route_table(VpcId=vpc_id)
    rtb_id = rtb["RouteTable"]["RouteTableId"]
    ec2.create_route(
        RouteTableId=rtb_id,
        DestinationCidrBlock="0.0.0.0/0",
        GatewayId=igw_id,
    )
    ec2.create_tags(
        Resources=[rtb_id],
        Tags=[
            {"Key": "Name", "Value": f"{PROJECT_TAG}-rtb"},
            {"Key": "Project", "Value": PROJECT_TAG},
        ],
    )

    # Associate route table with both subnets
    for subnet_id in subnet_ids:
        ec2.associate_route_table(RouteTableId=rtb_id, SubnetId=subnet_id)
    print(f"  Created Route Table: {rtb_id} (associated with both subnets)")

    return {"vpc_id": vpc_id, "subnet_ids": subnet_ids, "igw_id": igw_id}


# ─────────────────────────────────────────────
# Step 2: Security Groups
# ─────────────────────────────────────────────
def setup_security_groups(ec2, vpc_id: str) -> dict:
    """Create security groups for Lambda, EFS, and RDS."""

    def find_sg(name: str) -> Optional[str]:
        sgs = ec2.describe_security_groups(
            Filters=[
                {"Name": "vpc-id", "Values": [vpc_id]},
                {"Name": "group-name", "Values": [name]},
            ]
        )["SecurityGroups"]
        return sgs[0]["GroupId"] if sgs else None

    # Lambda SG
    lambda_sg_name = f"{PROJECT_TAG}-lambda-sg"
    lambda_sg_id = find_sg(lambda_sg_name)
    if not lambda_sg_id:
        resp = ec2.create_security_group(
            GroupName=lambda_sg_name,
            Description="Security group for Lambda functions",
            VpcId=vpc_id,
        )
        lambda_sg_id = resp["GroupId"]
        # Lambda SG: outbound all (default), no special inbound needed
        print(f"  Created Lambda SG: {lambda_sg_id}")
    else:
        print(f"  Lambda SG already exists: {lambda_sg_id}")

    # EFS SG
    efs_sg_name = f"{PROJECT_TAG}-efs-sg"
    efs_sg_id = find_sg(efs_sg_name)
    if not efs_sg_id:
        resp = ec2.create_security_group(
            GroupName=efs_sg_name,
            Description="Security group for EFS - allows NFS from Lambda",
            VpcId=vpc_id,
        )
        efs_sg_id = resp["GroupId"]
        # Allow NFS (port 2049) from Lambda SG
        ec2.authorize_security_group_ingress(
            GroupId=efs_sg_id,
            IpPermissions=[
                {
                    "IpProtocol": "tcp",
                    "FromPort": 2049,
                    "ToPort": 2049,
                    "UserIdGroupPairs": [{"GroupId": lambda_sg_id}],
                }
            ],
        )
        print(f"  Created EFS SG: {efs_sg_id} (NFS from Lambda SG)")
    else:
        print(f"  EFS SG already exists: {efs_sg_id}")

    # RDS SG
    rds_sg_name = f"{PROJECT_TAG}-rds-sg"
    rds_sg_id = find_sg(rds_sg_name)
    if not rds_sg_id:
        resp = ec2.create_security_group(
            GroupName=rds_sg_name,
            Description="Security group for RDS - allows MySQL from Lambda + external",
            VpcId=vpc_id,
        )
        rds_sg_id = resp["GroupId"]
        ec2.authorize_security_group_ingress(
            GroupId=rds_sg_id,
            IpPermissions=[
                # Allow MySQL from Lambda SG
                {
                    "IpProtocol": "tcp",
                    "FromPort": 3306,
                    "ToPort": 3306,
                    "UserIdGroupPairs": [{"GroupId": lambda_sg_id}],
                },
                # Allow MySQL from anywhere (for external dev access)
                # In production, restrict to your IP: "CidrIp": "YOUR_IP/32"
                {
                    "IpProtocol": "tcp",
                    "FromPort": 3306,
                    "ToPort": 3306,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "External MySQL access"}],
                },
            ],
        )
        print(f"  Created RDS SG: {rds_sg_id} (MySQL from Lambda SG + external)")
    else:
        print(f"  RDS SG already exists: {rds_sg_id}")

    return {
        "lambda_sg_id": lambda_sg_id,
        "efs_sg_id": efs_sg_id,
        "rds_sg_id": rds_sg_id,
    }


# ─────────────────────────────────────────────
# Step 3: EFS + Access Point + Mount Targets
# ─────────────────────────────────────────────
def setup_efs(session, vpc_id: str, subnet_ids: list, efs_sg_id: str) -> dict:
    """Create EFS file system, access point, and mount targets."""
    efs = session.client("efs")

    # Check if EFS already exists
    filesystems = efs.describe_file_systems()["FileSystems"]
    existing = [
        fs for fs in filesystems
        for tag in fs.get("Tags", [])
        if tag["Key"] == "Project" and tag["Value"] == PROJECT_TAG
    ]

    if existing:
        fs_id = existing[0]["FileSystemId"]
        print(f"  EFS already exists: {fs_id}")

        # Get access point
        aps = efs.describe_access_points(FileSystemId=fs_id)["AccessPoints"]
        ap_arn = aps[0]["AccessPointArn"] if aps else None

        return {"efs_id": fs_id, "access_point_arn": ap_arn}

    # Create EFS file system
    resp = efs.create_file_system(
        PerformanceMode="generalPurpose",
        ThroughputMode="bursting",
        Encrypted=True,
        Tags=[
            {"Key": "Name", "Value": f"{PROJECT_TAG}-efs"},
            {"Key": "Project", "Value": PROJECT_TAG},
        ],
    )
    fs_id = resp["FileSystemId"]
    print(f"  Created EFS: {fs_id}")

    # Wait for EFS to be available
    print("  Waiting for EFS to be available...")
    while True:
        status = efs.describe_file_systems(FileSystemId=fs_id)["FileSystems"][0]["LifeCycleState"]
        if status == "available":
            break
        time.sleep(3)

    # Create mount targets in each subnet
    for subnet_id in subnet_ids:
        try:
            efs.create_mount_target(
                FileSystemId=fs_id,
                SubnetId=subnet_id,
                SecurityGroups=[efs_sg_id],
            )
            print(f"  Created mount target in {subnet_id}")
        except efs.exceptions.MountTargetConflict:
            print(f"  Mount target already exists in {subnet_id}")

    # Create access point with /data root and posix user
    ap = efs.create_access_point(
        FileSystemId=fs_id,
        PosixUser={"Uid": 1000, "Gid": 1000},
        RootDirectory={
            "Path": "/data",
            "CreationInfo": {
                "OwnerUid": 1000,
                "OwnerGid": 1000,
                "Permissions": "755",
            },
        },
        Tags=[
            {"Key": "Name", "Value": f"{PROJECT_TAG}-ap"},
            {"Key": "Project", "Value": PROJECT_TAG},
        ],
    )
    ap_arn = ap["AccessPointArn"]
    print(f"  Created Access Point: {ap_arn}")

    # Wait for mount targets to be available
    print("  Waiting for mount targets to be available...")
    while True:
        mts = efs.describe_mount_targets(FileSystemId=fs_id)["MountTargets"]
        if all(mt["LifeCycleState"] == "available" for mt in mts):
            break
        time.sleep(5)
    print("  All mount targets available.")

    return {"efs_id": fs_id, "access_point_arn": ap_arn}


# ─────────────────────────────────────────────
# Step 4: RDS MySQL
# ─────────────────────────────────────────────
def setup_rds(session, subnet_ids: list, rds_sg_id: str) -> dict:
    """Create RDS MySQL instance (publicly accessible)."""
    rds = session.client("rds")

    # Check if RDS already exists
    try:
        resp = rds.describe_db_instances(DBInstanceIdentifier=RDS_INSTANCE_ID)
        instance = resp["DBInstances"][0]
        endpoint = instance["Endpoint"]["Address"]
        port = instance["Endpoint"]["Port"]
        print(f"  RDS already exists: {endpoint}:{port}")
        return {
            "rds_endpoint": endpoint,
            "rds_port": port,
            "rds_user": RDS_MASTER_USER,
            "rds_password": RDS_MASTER_PASSWORD,
        }
    except rds.exceptions.DBInstanceNotFoundFault:
        pass

    # Create DB Subnet Group
    subnet_group_name = f"{PROJECT_TAG}-subnet-group"
    try:
        rds.describe_db_subnet_groups(DBSubnetGroupName=subnet_group_name)
        print(f"  DB Subnet Group already exists: {subnet_group_name}")
    except rds.exceptions.DBSubnetGroupNotFoundFault:
        rds.create_db_subnet_group(
            DBSubnetGroupName=subnet_group_name,
            DBSubnetGroupDescription=f"Subnet group for {PROJECT_TAG}",
            SubnetIds=subnet_ids,
        )
        print(f"  Created DB Subnet Group: {subnet_group_name}")

    # Create RDS instance
    print("  Creating RDS MySQL instance (this takes 5-10 minutes)...")
    rds.create_db_instance(
        DBInstanceIdentifier=RDS_INSTANCE_ID,
        DBInstanceClass=RDS_INSTANCE_CLASS,
        Engine="mysql",
        EngineVersion="8.0",
        MasterUsername=RDS_MASTER_USER,
        MasterUserPassword=RDS_MASTER_PASSWORD,
        AllocatedStorage=20,
        DBSubnetGroupName=subnet_group_name,
        VpcSecurityGroupIds=[rds_sg_id],
        PubliclyAccessible=True,
        BackupRetentionPeriod=1,
        MultiAZ=False,
        StorageType="gp3",
        Tags=[
            {"Key": "Name", "Value": f"{PROJECT_TAG}-rds"},
            {"Key": "Project", "Value": PROJECT_TAG},
        ],
    )
    print(f"  RDS instance '{RDS_INSTANCE_ID}' is being created...")

    # Wait for RDS to be available
    print("  Waiting for RDS to be available (5-10 min)...")
    waiter = rds.get_waiter("db_instance_available")
    waiter.wait(
        DBInstanceIdentifier=RDS_INSTANCE_ID,
        WaiterConfig={"Delay": 30, "MaxAttempts": 40},
    )

    resp = rds.describe_db_instances(DBInstanceIdentifier=RDS_INSTANCE_ID)
    instance = resp["DBInstances"][0]
    endpoint = instance["Endpoint"]["Address"]
    port = instance["Endpoint"]["Port"]
    print(f"  RDS available: {endpoint}:{port}")

    return {
        "rds_endpoint": endpoint,
        "rds_port": port,
        "rds_user": RDS_MASTER_USER,
        "rds_password": RDS_MASTER_PASSWORD,
    }


# ─────────────────────────────────────────────
# Step 5: Update .env
# ─────────────────────────────────────────────
def update_env(config: dict):
    """Update .env file with new infrastructure config."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

    # Read current .env
    with open(env_path) as f:
        content = f.read()

    # Build new lines to append/replace
    infra_block = f"""
# ─── Infrastructure (auto-generated by setup_infra.py) ───
# IAM Role
AWS_LAMBDA_ROLE_ARN={config["role_arn"]}

# MySQL → RDS (same VPC as Lambda)
MYSQL_HOST={config["rds_endpoint"]}
MYSQL_PORT={config["rds_port"]}
MYSQL_USER={config["rds_user"]}
MYSQL_PASSWORD={config["rds_password"]}

# VPC & Lambda Networking
VPC_ID={config["vpc_id"]}
LAMBDA_SUBNET_IDS={",".join(config["subnet_ids"])}
LAMBDA_SECURITY_GROUP_ID={config["lambda_sg_id"]}

# EFS Configuration
EFS_FILE_SYSTEM_ID={config["efs_id"]}
EFS_ACCESS_POINT_ARN={config["access_point_arn"]}
EFS_MOUNT_PATH=/mnt/efs
"""

    # Remove old MySQL config and old infra block if exists
    lines = content.split("\n")
    new_lines = []
    skip = False
    for line in lines:
        # Skip old infra block
        if "auto-generated by setup_infra.py" in line:
            skip = True
            continue
        if skip:
            # End of infra block (next non-empty section or blank+comment)
            if line.strip() == "" and not skip:
                skip = False
            elif line.startswith("# ") and "Infrastructure" not in line and not line.startswith("# MySQL") and not line.startswith("# VPC") and not line.startswith("# EFS"):
                skip = False
                new_lines.append(line)
            elif line.startswith("MYSQL_HOST=") or line.startswith("MYSQL_PORT=") or line.startswith("MYSQL_USER=") or line.startswith("MYSQL_PASSWORD=") or line.startswith("VPC_ID=") or line.startswith("LAMBDA_SUBNET") or line.startswith("LAMBDA_SECURITY") or line.startswith("EFS_"):
                continue
            elif line.strip() == "":
                continue
            else:
                skip = False
                new_lines.append(line)
            continue

        # Skip old MySQL lines
        if line.startswith("MYSQL_HOST=") or line.startswith("MYSQL_PORT=") or line.startswith("MYSQL_USER=") or line.startswith("MYSQL_PASSWORD="):
            continue
        # Skip old commented MySQL/RDS lines
        if line.startswith("# MYSQL_HOST=") or line.startswith("# MYSQL_PORT=") or line.startswith("# MYSQL_USER=") or line.startswith("# MYSQL_PASSWORD="):
            continue
        # Skip old section headers
        if line.strip() == "# MySQL Configuration":
            continue
        # Skip old IAM role lines
        if line.startswith("AWS_LAMBDA_ROLE_ARN="):
            continue
        if line.strip() == "# AWS Lambda IAM Role":
            continue

        new_lines.append(line)

    # Clean up trailing blank lines
    while new_lines and new_lines[-1].strip() == "":
        new_lines.pop()

    final = "\n".join(new_lines) + "\n" + infra_block

    with open(env_path, "w") as f:
        f.write(final)

    print(f"  Updated {env_path}")


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  AWS Infrastructure Setup: IAM + VPC + EFS + RDS")
    print("=" * 60)

    session = get_session()
    ec2 = session.client("ec2")

    # Step 1: IAM Role
    print("\n[1/6] Setting up IAM Role...")
    iam_info = setup_iam_role(session)

    # Step 2: VPC
    print("\n[2/6] Setting up VPC + Subnets + Internet Gateway...")
    vpc_info = setup_vpc(ec2)
    vpc_id = vpc_info["vpc_id"]
    subnet_ids = vpc_info["subnet_ids"]

    # Step 3: Security Groups
    print("\n[3/6] Setting up Security Groups...")
    sg_info = setup_security_groups(ec2, vpc_id)

    # Step 4: EFS
    print("\n[4/6] Setting up EFS + Access Point + Mount Targets...")
    efs_info = setup_efs(session, vpc_id, subnet_ids, sg_info["efs_sg_id"])

    # Step 5: RDS
    print("\n[5/6] Setting up RDS MySQL...")
    rds_info = setup_rds(session, subnet_ids, sg_info["rds_sg_id"])

    # Step 6: Update .env
    print("\n[6/6] Updating .env file...")
    config = {
        **iam_info,
        **vpc_info,
        **sg_info,
        **efs_info,
        **rds_info,
    }
    update_env(config)

    # Save full config to JSON for reference
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTPUT_FILE)
    with open(output_path, "w") as f:
        json.dump(config, f, indent=2, default=str)
    print(f"  Saved full config to {output_path}")

    # Summary
    print("\n" + "=" * 60)
    print("  SETUP COMPLETE!")
    print("=" * 60)
    print(f"""
  IAM Role:     {iam_info["role_arn"]}
  VPC:          {vpc_id}
  Subnets:      {", ".join(subnet_ids)}
  Lambda SG:    {sg_info["lambda_sg_id"]}
  EFS SG:       {sg_info["efs_sg_id"]}
  RDS SG:       {sg_info["rds_sg_id"]}
  EFS ID:       {efs_info["efs_id"]}
  EFS AP ARN:   {efs_info["access_point_arn"]}
  RDS Endpoint: {rds_info["rds_endpoint"]}:{rds_info["rds_port"]}
  RDS User:     {rds_info["rds_user"]}
""")


if __name__ == "__main__":
    main()
