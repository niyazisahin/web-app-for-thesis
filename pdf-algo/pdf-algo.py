
import slate3k as slate
from pprint import pprint


def get_info_from_pdf(pdf_path):
    
    with open("örnek.pdf",'rb') as f:
        extracted_text = slate.PDF(f)

    result = {'yazar':[], 'danısman':[], 'juri':[]}

    tmp = ""
    for line in extracted_text[3].lower().split("\n"):
        tmp += line.strip() + ":" if (":" in line) and ("i̇mza" not in line) else ""
    tmp = tmp.split(':')[1::2]
    for i in range(0, len(tmp), 2):
        result["yazar"].append({'ad':tmp[i+1], 'numara':tmp[i]})

    page1 = [i.strip().lower() for i in extracted_text[1].split('\n') if (i != '')]
    
    result['ders ad'] = page1[3]
    result['proje baslik'] = page1[4]

    for i in range(len(page1)):
        if 'danışman' in page1[i]:
            result['danısman'].append(page1[i-1])
            result['juri'].append(page1[i-1])
        if 'jüri' in page1[i]:
            result['juri'].append(page1[i-1])
        if 'tarih' in page1[i]:
            result['tez tarih'] = page1[i].split(':')[1].strip()

    _, rest = extracted_text[10].lower().split('özet', 1)
    özet, anahtar = rest.split('anahtar kelimeler:')
    

    result['ozet'] = "".join(özet)
    result['anahtar'] = list(filter(None, [i.strip() for i in (anahtar.replace('\n', ',').replace('.', ',').split(',')) if(i!='ix')]))
    return result
    

pprint(get_info_from_pdf("örnek.pdf"))