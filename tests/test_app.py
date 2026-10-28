import base64
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server


class WorkflowTests(unittest.TestCase):
    def test_pdf_text_and_reference(self):
        import io
        from pypdf import PdfWriter
        from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
        writer = PdfWriter()
        page = writer.add_blank_page(width=500, height=500)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
        stream = DecodedStreamObject()
        stream.set_data(b'BT /F1 12 Tf 50 450 Td (Prim: 12000 TL - Muafiyet: %2) Tj ET')
        page[NameObject('/Contents')] = writer._add_object(stream)
        output = io.BytesIO()
        writer.write(output)
        result = server.extract_document('teklif.pdf', base64.b64encode(output.getvalue()).decode())
        self.assertEqual(result['findings']['Muafiyet'][0]['page'], 1)
        self.assertIn('12000 TL', result['findings']['Prim / ödeme'][0]['text'])

    def test_quote_references_and_missing_fields(self):
        text = 'Toplam prim: 12.000 TL\nCam teminatı: dahil\nDeprem muafiyeti: %2\n'
        result = server.extract_document('teklif.txt', base64.b64encode(text.encode()).decode())
        self.assertEqual(result['findings']['Muafiyet'], [{'page': 1, 'text': 'Deprem muafiyeti: %2'}])
        self.assertEqual(result['findings']['Prim / ödeme'][0]['text'], 'Toplam prim: 12.000 TL')
        self.assertEqual(result['findings']['İstisna / özel şart'], [])

    def test_scanned_or_empty_document_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Metin okunamadı'):
            server.extract_document('bos.txt', base64.b64encode(b' ').decode())

    def test_shared_task_persists_between_connections(self):
        old = server.DB
        try:
            with tempfile.TemporaryDirectory() as directory:
                server.DB = Path(directory) / 'test.db'
                with server.connect() as con:
                    con.execute('INSERT INTO tasks(customer,branch,detail) VALUES (?,?,?)', ('Deneme', 'Kasko', 'Yenileme'))
                with server.connect() as con:
                    row = con.execute('SELECT * FROM tasks').fetchone()
                self.assertEqual(row['customer'], 'Deneme')
                self.assertEqual(row['status'], 'Bekliyor')
        finally:
            server.DB = old


if __name__ == '__main__':
    unittest.main()
