# Auto Subtitle Studio

แอปถอดไฟล์เสียงเป็นซับ `.srt` แบบคำต่อคำหรือวลีสั้น ๆ พร้อมเวลา ใช้ทำ Kinetic Subtitle

แอปนี้อยู่คนละโฟลเดอร์กับ Mystery Content Generator ไม่ได้ยุ่งกับไฟล์แอปเดิม

## สิ่งที่ต้องมี

1. ติดตั้ง Python จาก [python.org](https://www.python.org/downloads/) แล้วติ๊ก **Add Python to PATH**
2. คีย์ Gemini จาก [Google AI Studio](https://aistudio.google.com/apikey)

## เปิดแอปแบบไม่ต้องเขียนโค้ด

### Windows

1. เปิดโฟลเดอร์ `auto-subtitle-studio`
2. คัดลอกไฟล์ `.env.example` แล้วเปลี่ยนชื่อเป็น `.env`
3. เปิด `.env` ด้วย Notepad แล้ววางคีย์หลังเครื่องหมาย `=`
4. ดับเบิลคลิก `start.bat`
5. รอจนขึ้นข้อความว่าแอปพร้อมแล้ว แล้วเปิดเบราว์เซอร์ไปที่ [http://127.0.0.1:8787](http://127.0.0.1:8787)

### Mac / Linux

1. เปิดโฟลเดอร์ `auto-subtitle-studio`
2. คัดลอก `.env.example` เป็น `.env` แล้วใส่คีย์
3. เปิด Terminal ในโฟลเดอร์นี้ แล้วรัน

```bash
chmod +x start.sh
./start.sh
```

4. เปิด [http://127.0.0.1:8787](http://127.0.0.1:8787)

## วิธีใช้

1. ลากไฟล์เสียงมาวาง (MP3, WAV, M4A, AAC, OGG, FLAC, WebM)
2. เลือกจำนวนคำต่อบรรทัด 1 / 2 / 3 / 4
3. กด **ถอดเสียงเป็นซับ**
4. แก้เวลาหรือข้อความในตารางได้
5. ดูตัวอย่าง `.srt` ด้านขวา แล้วกดดาวน์โหลด `subtitles.srt`

คีย์ถูกอ่านจากไฟล์ `.env` ตัวแปร `GEMINI_API_KEY` เท่านั้น หน้าเว็บไม่มีช่องกรอกคีย์ และไฟล์ `.env` จะไม่ถูกส่งขึ้น git

หลังถอดเสียง แอปจะลบไฟล์ชั่วคราวในเครื่อง และลบไฟล์ที่อัปโหลดขึ้น Gemini Files API ให้เอง

ใช้โมเดล `gemini-3.5-transcribe` พร้อม word-level timestamps ไม่ได้เรียก OpenAI
