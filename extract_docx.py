import os
import zipfile
import xml.etree.ElementTree as ET

def get_docx_paragraphs(path):
    try:
        with zipfile.ZipFile(path) as docx:
            xml_content = docx.read('word/document.xml')
            root = ET.fromstring(xml_content)
            paragraphs = []
            for elem in root.iter():
                if elem.tag.endswith('p'):
                    p_text = []
                    for child in elem.iter():
                        if child.tag.endswith('t') and child.text:
                            p_text.append(child.text)
                    if p_text:
                        paragraphs.append(''.join(p_text))
            return paragraphs
    except Exception as e:
        return [f'Error reading {path}: {str(e)}']

downloads = r'c:\Users\kbpra\Downloads'
files = {
    'intro.txt': os.path.join(downloads, r'lab_notes\Introduction.docx'),
    'suresh.txt': os.path.join(downloads, 'suresh.docx'),
    'jagadeesh.txt': os.path.join(downloads, 'jagadeesh.docx'),
}

for txt_name, docx_path in files.items():
    if os.path.exists(docx_path):
        paragraphs = get_docx_paragraphs(docx_path)
        with open(txt_name, 'w', encoding='utf-8') as f:
            f.write('\n'.join(paragraphs))
        print(f'Extracted {docx_path} to {txt_name} ({len(paragraphs)} paragraphs)')
    else:
        print(f'File not found: {docx_path}')
