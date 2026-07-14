SYSTEM_PROMPT = """คุณเป็น "ผู้ช่วยจัดการสินทรัพย์" สำหรับลูกค้าสูงอายุ (อายุ 60 ปีขึ้นไป)

## บทบาทของคุณ
- ช่วยตอบคำถามเกี่ยวกับบัญชี ยอดเงิน ธุรกรรม และพอร์ตการลงทุน
- ให้ข้อมูลที่ถูกต้อง โดยอ้างอิงจากข้อมูลจริงเท่านั้น
- ใช้ภาษาที่เข้าใจง่าย หลีกเลี่ยงศัพท์เทคนิค
- เสนอทางเลือกให้พูดคุยกับเจ้าหน้าที่เสมอ

## กฎเหล็ก
1. ห้ามสร้างตัวเลขเอง — ทุกตัวเลขต้องมาจาก tool outputs เท่านั้น
2. ห้ามทำธุรกรรมทางการเงิน (โอน ถอน ซื้อขาย) — ต้องส่งต่อเจ้าหน้าที่
3. ห้ามให้คำแนะนำการลงทุนเฉพาะเจาะจง (ห้ามบอกว่าควรซื้อ/ขายอะไร)
4. ห้ามให้ข้อมูลเกี่ยวกับสินทรัพย์ดิจิทัล/cryptocurrency
5. ถ้าข้อมูลอาจไม่เป็นปัจจุบัน (stale) ต้องแจ้งลูกค้า
6. ถ้ามีธุรกรรมซ้ำซ้อน ต้องแจ้งลูกค้าและแนะนำตรวจสอบ

## รูปแบบการตอบ
- ตอบเป็นภาษาเดียวกับคำถาม (ปกติเป็นภาษาไทย)
- แสดงจำนวนเงินเป็นตัวเลขที่อ่านง่ายพร้อมหน่วย "บาท"
- ไม่เร่งรัดลูกค้าในการตัดสินใจ
- ลงท้ายด้วยการเสนอความช่วยเหลือเพิ่มเติม"""


RESPONSE_GENERATION_PROMPT = """จากข้อมูลที่ได้จาก tools ให้สร้างคำตอบสำหรับลูกค้าสูงอายุ

## ข้อความของลูกค้า
{user_message}

## ข้อมูลจาก Tools
{tool_data}

## คำแนะนำในการตอบ
- ตอบเป็นภาษาเดียวกับคำถามของลูกค้า
- อ้างอิงข้อมูลจาก tool outputs เท่านั้น ห้ามสร้างตัวเลขเอง
- แสดงจำนวนเงินเป็นรูปแบบที่อ่านง่าย (เช่น 435,987.50 บาท)
- ใช้ภาษาที่เข้าใจง่าย หลีกเลี่ยงศัพท์เทคนิค
- ถ้าข้อมูลอาจไม่สมบูรณ์ ให้แจ้งลูกค้า
- ถ้ามีข้อมูล support_case (เลขที่เคส case_id) ให้แจ้งลูกค้าว่าสร้างเคสแล้วพร้อมเลขที่เคส และเวลาที่คาดว่าเจ้าหน้าที่จะติดต่อกลับ
- ลงท้ายด้วยการเสนอความช่วยเหลือเพิ่มเติมหรือแนะนำให้ติดต่อเจ้าหน้าที่

ตอบเป็นข้อความธรรมชาติ ไม่ต้องใส่ JSON หรือ markdown formatting"""


GRACEFUL_DEGRADATION_TEMPLATE = """ขออภัยค่ะ ขณะนี้ระบบไม่สามารถเข้าถึง{service}ได้ชั่วคราว

สิ่งที่ท่านสามารถทำได้:
- ลองถามใหม่อีกครั้งในอีกสักครู่
- ติดต่อเจ้าหน้าที่โดยตรงที่ 02-xxx-xxxx

ขออภัยในความไม่สะดวกค่ะ"""


def format_tool_data_for_prompt(tool_outputs: dict) -> str:
    parts = []

    for tool_name, output in tool_outputs.items():
        if output is None:
            parts.append(f"### {tool_name}\nไม่สามารถดึงข้อมูลได้ (timeout)")
            continue

        if isinstance(output, list):
            parts.append(f"### {tool_name}\nจำนวน: {len(output)} รายการ")
            for i, item in enumerate(output[:10]):
                parts.append(f"  {i+1}. {_format_item(item)}")
            if len(output) > 10:
                parts.append(f"  ... และอีก {len(output) - 10} รายการ")
        elif isinstance(output, dict):
            parts.append(f"### {tool_name}")
            for key, value in output.items():
                if isinstance(value, list):
                    parts.append(f"  {key}: {len(value)} รายการ")
                    for item in value[:5]:
                        parts.append(f"    - {_format_item(item)}")
                else:
                    parts.append(f"  {key}: {value}")
        else:
            parts.append(f"### {tool_name}\n{output}")

    return "\n\n".join(parts)


def _format_item(item: dict | str) -> str:
    if isinstance(item, dict):
        parts = [f"{key}={value}" for key, value in item.items()]
        return ", ".join(parts) if parts else str(item)
    return str(item)
