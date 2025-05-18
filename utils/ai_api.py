import base64
import os
from google import genai
import json
from google.genai import types


def generate(veri):

    binalar = veri["etkilenen_binalar"]
    etkilenen_bina_sayisi = int(veri["etkilenen_bina_sayisi"])
    genc_nufus = int(veri["genc_nufus"])
    genc_nufus_orani = int(veri["genc_nufus_orani"])
    yasli_nufus = int(veri["yasli_nufus"])
    yasli_nufus_orani = int(veri["yasli_nufus_orani"])

    


    prompt_orj = veri["prompt"] # belirtilen sokak üzerinde 5 saat kadar süren bir elektrik kesintisi meydana geldi. 

    prompt = f"""
    Altyapıdan sorumlu bir görevlisin. 
    En önemli görevin, görevli olduğun şehirde hafif-ortalama yoğunlukta bir sokakta 5 saat süren bir elektrik kesintisi meydana geldi. 
    
    Bu sorun karşısında meydana gelebilecek potansiyel ek sorunlar nedir ? 
    Bu sorunlara en hızlı çözümü nasıl üretirsin ? 
    Bu sorunlara üretilebilecek kalıcı çözüm önerilerin nedir ? 
    Çevrede olan işletmeler: {binalar}; durumdan etkilenen bina adeti: {etkilenen_bina_sayisi}; 
    bu durumdan etkilenebilecek tahmini genç nüfus: {genc_nufus}; 
    bu durumdan etkilenebilecek tahmini genç nüfusun bütün gençlere oranı: {genc_nufus_orani};
    bu durumdan etkilenebilecek tahmini yetişkin nüfus:{yasli_nufus};
    bu durumdan etkilenebilecek tahmini yetişkinlerin bütün yetişkinlere oranı:{yasli_nufus_orani}"""
    

    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = "gemini-2.0-flash"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
                #types.Part.from_text(text="""INSERT_INPUT_HERE"""),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=1.4,
        response_mime_type="application/json",
        response_schema=genai.types.Schema(
            type = genai.types.Type.OBJECT,
            required = ["etkilenebilecek_yapilar", "hizli_onlemler", "dort_potansiyel_ozet_sonuclar", "potansiyel_ek_sonuclar", "altyapiyi_iyilestirmek_icin_yapilabilecekler"],
            properties = {
                "etkilenebilecek_yapilar": genai.types.Schema(
                    type = genai.types.Type.ARRAY,
                    items = genai.types.Schema(
                        type = genai.types.Type.OBJECT,
                        required = ["yapi_adi", "aciklama", "mdi_icon"],
                        properties = {
                            "yapi_adi": genai.types.Schema(
                                type = genai.types.Type.STRING,
                            ),
                            "aciklama": genai.types.Schema(
                                type = genai.types.Type.STRING,
                            ),
                            "mdi_icon": genai.types.Schema(
                                type = genai.types.Type.STRING,
                            ),
                        },
                    ),
                ),
                "hizli_onlemler": genai.types.Schema(
                    type = genai.types.Type.ARRAY,
                    items = genai.types.Schema(
                        type = genai.types.Type.STRING,
                    ),
                ),
                "dort_potansiyel_ozet_sonuclar": genai.types.Schema(
                    type = genai.types.Type.ARRAY,
                    items = genai.types.Schema(
                        type = genai.types.Type.OBJECT,
                        required = ["baslik", "mdi_icon", "olumlu_mu", "tahmini_deger", "birim"],
                        properties = {
                            "baslik": genai.types.Schema(
                                type = genai.types.Type.STRING,
                            ),
                            "mdi_icon": genai.types.Schema(
                                type = genai.types.Type.STRING,
                            ),
                            "olumlu_mu": genai.types.Schema(
                                type = genai.types.Type.BOOLEAN,
                            ),
                            "tahmini_deger": genai.types.Schema(
                                type = genai.types.Type.INTEGER,
                            ),
                            "birim": genai.types.Schema(
                                type = genai.types.Type.STRING,
                            ),
                        },
                    ),
                ),
                "potansiyel_ek_sonuclar": genai.types.Schema(
                    type = genai.types.Type.ARRAY,
                    items = genai.types.Schema(
                        type = genai.types.Type.OBJECT,
                        required = ["baslik", "aciklama"],
                        properties = {
                            "baslik": genai.types.Schema(
                                type = genai.types.Type.STRING,
                            ),
                            "aciklama": genai.types.Schema(
                                type = genai.types.Type.STRING,
                            ),
                        },
                    ),
                ),
                "altyapiyi_iyilestirmek_icin_yapilabilecekler": genai.types.Schema(
                    type = genai.types.Type.ARRAY,
                    items = genai.types.Schema(
                        type = genai.types.Type.STRING,
                    ),
                ),
            },
        ),
    )

    cikti = ""
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):

        cikti += chunk.text
    return cikti

