import json
import os
import qrcode


def generate_qr_codes(json_file="spreadsheet.json", output_dir="qr_codes"):
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    os.makedirs(output_dir, exist_ok=True)

    total = 0
    for building, rooms in data.items():
        building_dir = os.path.join(output_dir, building)
        os.makedirs(building_dir, exist_ok=True)

        for room in rooms:
            room_code = room["Room"]
            img = qrcode.make(room_code)
            filename = f"{room_code}.png"
            img.save(os.path.join(building_dir, filename))
            total += 1

        print(f"{building}: {len(rooms)} QR codes")

    print(f"\nTổng: {total} QR codes -> {output_dir}/")


if __name__ == "__main__":
    generate_qr_codes()
