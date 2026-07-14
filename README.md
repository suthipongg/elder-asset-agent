# Elder Asset Agent

ผู้ช่วย AI สำเร็จรูปสำหรับจัดการสินทรัพย์และบัญชีสำหรับลูกค้าผู้สูงอายุ
โครงการนี้ออกแบบมาเพื่อตอบคำถามทางการเงิน ตรวจสอบพอร์ตการลงทุน ยอดเงิน ธุรกรรมย้อนหลัง และแนะนำการเปิดบัญชีใหม่ ผ่าน AI Agentic Loop (ReAct style) ที่แม่นยำ ปลอดภัย และมีการป้องกันความเสี่ยง (Fraud Detection & Compliance Gate) อย่างเข้มงวด

## โครงสร้างโปรเจค

- `start.sh` - สคริปต์สำหรับติดตั้งและรันระบบอัตโนมัติ (แนะนำ)
- `elder-asset-agent/` - Source code หลักของระบบแชทบอท
  - `agent/` - ลอจิกหลักของ Agent (Agentic Loop, Prompts, Classification, Deduplication)
  - `tools/` - Mock APIs (ดึงข้อมูลบัญชี, พอร์ต, ธุรกรรม, สร้างเคส ฯลฯ)
  - `data/` - Mock database (ไฟล์ JSON)
  - `tests/` - ชุดทดสอบ (Unit Tests) กว่า 87 เคส
  - `docs/` - เอกสารการออกแบบระบบ (System Design)
- `assignment/` - ไฟล์และเอกสารเกี่ยวกับโจทย์
- `test_txt/` - ไฟล์สำหรับทดสอบคำถามต่างๆ

## การติดตั้งและใช้งาน

### วิธีที่ง่ายที่สุด (รันอัตโนมัติ)

สร้างไฟล์ `.env` และใส่คีย์ `GEMINI_API_KEY`:

```bash
cp elder-asset-agent/.env.example elder-asset-agent/.env
# เปิดไฟล์ elder-asset-agent/.env แล้วใส่ค่า API Key ลงไป
```

แล้วคุณสามารถรันโปรเจคนี้ได้อย่างง่ายดายผ่านสคริปต์ `start.sh` ที่จะทำหน้าที่สร้าง Virtual Environment, ลง Dependencies และเปิดตัว Chatbot ให้อัตโนมัติ:

```bash
# ตรวจสอบและรันสคริปต์
chmod +x start.sh
./start.sh
```

> [!IMPORTANT]
> ระบบต้องการ **GEMINI_API_KEY** ในการทำงาน
> หากรันครั้งแรก ระบบจะทำการสร้างไฟล์ `elder-asset-agent/.env` ให้อัตโนมัติ (จาก .env.example)
> กรุณานำ API Key ของคุณไปใส่ในไฟล์นั้นก่อนการรันครั้งต่อไป

### วิธีแบบ Manual (รันทีละขั้นตอน)

1. เข้าไปที่โฟลเดอร์หลักของโปรแกรม:

```bash
cd elder-asset-agent
```

2. สร้างและใช้งาน Virtual Environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

3. ติดตั้ง Library ที่จำเป็น:

```bash
pip install -r requirements.txt
```

4. สร้างไฟล์ `.env` และใส่คีย์ `GEMINI_API_KEY`:

```bash
cp .env.example .env
# เปิดไฟล์ .env แล้วใส่ค่า API Key ลงไป
```

5. รันโปรแกรมแชทบอท:

```bash
python chat.py
```

## การทดสอบระบบ (Unit Testing)

ระบบถูกทดสอบอย่างครอบคลุมเพื่อให้มั่นใจว่าปลอดภัยและถูกต้องแม่นยำ สามารถรันเทสได้โดยเข้าโฟลเดอร์ `elder-asset-agent` แล้วพิมพ์คำสั่ง:

```bash
pytest tests/ -v
```
