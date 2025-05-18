from flask import Flask, render_template, request, jsonify
import model.read as k_model
import time
import requests
from shapely.geometry import Polygon, LineString, Point, shape, mapping
from shapely.ops import unary_union
import json
import utils.ai_api as aistdio


app = Flask(__name__, static_folder='assets')


with open("nufus_veri.json", "r") as nufus_veri_file:
    mahalle_nufus_veri = json.loads(nufus_veri_file.read())




def text_tabanli(data):
    addres = data["prompt"].split("/")[0].split(",")
    prompt = data["prompt"].split("/")[1]
    durum_katsayi = (k_model.tahmini_etki_alani(prompt))

    city = addres[0]
    street = addres[1]

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'city': city,
        'street': street,
        'country': 'Turkey',
        'format': 'json',
        'limit': 1,
        'polygon_geojson': 1 
    }
    headers = {
        'User-Agent': 'Mozilla/5.0'  # Zorunlu başlık
    }
    
    response = requests.get(url, params=params, headers=headers)
    data = response.json()

    
    lat = data[0]['lat']
    lon = data[0]['lon']
    

    return {"mode":"address_search","address":{"coordinate_lat":data[0]['lat'],"coordinate_lon":data[0]['lon']}, "_line": data[0]["geojson"], "_prompt":prompt}



def ikincil_derece_alan(coords, genisletme_miktari=0.0002):
    #poly = Polygon(coords)
    poly = Polygon(coords["coordinates"][0])  # coordinates[0] içindeki liste polygon köşeleri
    genisletilmis_poly = poly.buffer(genisletme_miktari)
    genisletilmis_coords = list(genisletilmis_poly.exterior.coords)
    return genisletilmis_coords

#Sivas, 11-14. Sokak /  ilgili konumda trafo patlaması nedeniyle bir elektrik kesintisi meydana geldi. sokak , cadde genelinde potansiyel ek sorunlar nelerdir ?

def ikincil_fetch_roads_from_area(geojson_polygon):
    try:
        polygon_shape = shape(geojson_polygon)
        minx, miny, maxx, maxy = polygon_shape.bounds

        query = f"""
        [out:json][timeout:120];
        (
        way["highway"]({miny},{minx},{maxy},{maxx});
        );
        (._;>;);
        out body;
        """

        url = "https://overpass-api.de/api/interpreter"
        response = requests.post(url, data=query, timeout=120)
        response.raise_for_status()
        data = response.json()

        elements = data.get("elements", [])

        # Node ve Way'leri ayır
        node_map = {el["id"]: el for el in elements if el["type"] == "node"}
        way_list = [el for el in elements if el["type"] == "way"]

        filtered_elements = []
        used_node_ids = set()

        for way in way_list:
            node_coords = []
            for node_id in way.get("nodes", []):
                node = node_map.get(node_id)
                if node:
                    node_coords.append((node["lon"], node["lat"]))

            if len(node_coords) >= 2:
                line = LineString(node_coords)
                if line.intersects(polygon_shape):
                    filtered_elements.append(way)
                    used_node_ids.update(way["nodes"])

        # Kullanılan node'ları da ekle
        for node_id in used_node_ids:
            node = node_map.get(node_id)
            if node:
                filtered_elements.append(node)

        return {
            "version": 0.6,
            "generator": "custom-filter",
            "osm3s": {},
            "elements": filtered_elements
        }
    except:
        polygon_shape = shape(geojson_polygon[0])
        minx, miny, maxx, maxy = polygon_shape.bounds

        query = f"""
        [out:json][timeout:120];
        (
        way["highway"]({miny},{minx},{maxy},{maxx});
        );
        (._;>;);
        out body;
        """

        url = "https://overpass-api.de/api/interpreter"
        response = requests.post(url, data=query, timeout=120)
        response.raise_for_status()
        data = response.json()

        elements = data.get("elements", [])

        # Node ve Way'leri ayır
        node_map = {el["id"]: el for el in elements if el["type"] == "node"}
        way_list = [el for el in elements if el["type"] == "way"]

        filtered_elements = []
        used_node_ids = set()

        for way in way_list:
            node_coords = []
            for node_id in way.get("nodes", []):
                node = node_map.get(node_id)
                if node:
                    node_coords.append((node["lon"], node["lat"]))

            if len(node_coords) >= 2:
                line = LineString(node_coords)
                if line.intersects(polygon_shape):
                    filtered_elements.append(way)
                    used_node_ids.update(way["nodes"])

        # Kullanılan node'ları da ekle
        for node_id in used_node_ids:
            node = node_map.get(node_id)
            if node:
                filtered_elements.append(node)

        return {
            "version": 0.6,
            "generator": "custom-filter",
            "osm3s": {},
            "elements": filtered_elements
        }



def fetch_buildings_from_area(geojson_data):

    try: # hizli cozum try-except:
        polygon_shape = Polygon(geojson_data["coordinates"][0])  # coordinates[0] içindeki liste polygon köşeleri
        minx, miny, maxx, maxy = polygon_shape.bounds

        query = f"""
        [out:json][timeout:120];
        (
        way["building"]({miny},{minx},{maxy},{maxx});
        );
        out body;
        >;
        out skel qt;
        """

        url = "https://overpass-api.de/api/interpreter"
        response = requests.post(url, data=query, timeout=120)
        response.raise_for_status()
        return response.json()
    except:


        line_shape = LineString(geojson_data[0]["coordinates"])
        minx, miny, maxx, maxy = line_shape.bounds

        query = f"""
        [out:json][timeout:120];
        (
        way["building"]({miny},{minx},{maxy},{maxx});
        way["building"]["building:levels"]({miny},{minx},{maxy},{maxx});

        );
        out body;
        >;
        out skel qt;
        """

        url = "https://overpass-api.de/api/interpreter"
        response = requests.post(url, data=query, timeout=120)
        response.raise_for_status()
        return response.json()


def bolge_tabanli(data):

    areas = data["areas"]
    prompt = data["prompt"]
    durum_katsayi = k_model.tahmini_etki_alani(prompt)
    yolanaliz = 0
    binaanaliz = 1


    if any(word in prompt.lower() for word in ["sokak", "cadde", "yol", "yolun"]):
        yolanaliz = 1

    if any(word in prompt.lower() for word in ["bina", "binalar", "binaların"]):
        binaanaliz = 1

    etkilenecek_binalar = []
    etkilenecek_yollar = []
    bolgeler = []
    
    toplam_genc_nufus = 0
    toplam_yetiskin_nufus = 0
    toplam_yetiskin_nufus_orani = 0
    toplam_genc_nufus_orani = 0

    

    for area in areas:
        geojson = area["geometry"]

        # mahalle tespit 
        try:
            ex_coor = geojson[0]["coordinates"][0]
            mahalle_veri = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={ex_coor[1]}&lon={ex_coor[0]}", headers={'User-Agent': 'MyAppName/1.0 (myemail@example.com)'}).json()
            mahalle = mahalle_veri["address"]["suburb"].split(" ")[0].lower()
        except:
            ex_coor = area["geometry"]["coordinates"][0][0]
            mahalle_veri = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={ex_coor[1]}&lon={ex_coor[0]}", headers={'User-Agent': 'MyAppName/1.0 (myemail@example.com)'}).json()
            mahalle = mahalle_veri["address"]["suburb"].split(" ")[0].lower()
        
        # ortalama_hane_halki = 3.24

        ortalama_hane_sayisi = mahalle_nufus_veri[mahalle]["ortalama_hane"]
        ortalama_bina_sayisi = int(ortalama_hane_sayisi / 4)
        mahalle_toplam_nufus = mahalle_nufus_veri[mahalle]["toplam_nufus"]

        mahalle_genc_nufus = mahalle_nufus_veri[mahalle]["eski_onsekiz"]
        mahalle_yetiskin_nufus = mahalle_nufus_veri[mahalle]["arti_onsekiz"]




        bolgeler.append({"elements":geojson})

        durumdan_etkilenen_genc_nufus = []
        durumdan_etkilenen_genc_nufus_orani = []
        durumdan_etkilenen_yetiskin_nufus = []
        durumdan_etkilenen_yetiskin_nufus_orani = []


        if binaanaliz:
            birincil_bolgedeki_binalar = []
            ikincil_bolgedeki_binalar = []
            # (birincil derece)


            birincil_bolgedeki_binalar = fetch_buildings_from_area(geojson)

            birincil_bolgedeki_bina_sayisi = sum(
                1 for element in birincil_bolgedeki_binalar["elements"]
                if element["type"] == "way" and "tags" in element and "building" in element["tags"]
            )

            ozel_bina_building = [
                "school", "hospital", "church", "yes", "kindergarten", "university", "college", "cathedral", "mosque",
                "temple", "train_station", "fire_station", "police", "prison", "library"
            ]

            ozel_bina_amenity = [
                "school", "place_of_worship", "hospital", "marketplace", "fire_station", "police", "prison", "library",
                "kindergarten", "university", "college"
            ]

            ozel_bina_shop = [
                "supermarket", "convenience", "bakery", "pharmacy"
            ]

            ozel_bina_religion = [
                "muslim", "christian", "jewish", "buddhist", "hindu"
            ]

            ozel_binalar = [
                element for element in birincil_bolgedeki_binalar["elements"]
                if element["type"] == "way" and "tags" in element and (
                    (element["tags"].get("building") in ozel_bina_building) or
                    (element["tags"].get("amenity") in ozel_bina_amenity) or
                    (element["tags"].get("shop") in ozel_bina_shop) or
                    (element["tags"].get("religion") in ozel_bina_religion)
                )
            ]
            ozel_bina_listesi = []

            for element in birincil_bolgedeki_binalar["elements"]:
                if element["type"] == "way" and "tags" in element:
                    tags = element["tags"]
                    if (
                        tags.get("building") in ozel_bina_building or
                        tags.get("amenity") in ozel_bina_amenity or
                        tags.get("shop") in ozel_bina_shop or
                        tags.get("religion") in ozel_bina_religion
                    ):
                        bina_adi = tags.get("name", "İsimsiz Bina")
                        ozel_bina_listesi.append({
                            "id": element.get("id"),
                            "name": bina_adi,
                            "tags": tags
                        })

            # Örnek çıktı
        
            durumdan_etkilenen_genc_nufus = (birincil_bolgedeki_bina_sayisi / ortalama_bina_sayisi) * mahalle_genc_nufus
            durumdan_etkilenen_genc_nufus_orani = round((durumdan_etkilenen_genc_nufus / mahalle_yetiskin_nufus) * 100,2)
            durumdan_etkilenen_genc_nufus = k_model.etkilenen_nufus_predict(durumdan_etkilenen_genc_nufus)

            durumdan_etkilenen_yetiskin_nufus = (birincil_bolgedeki_bina_sayisi / ortalama_bina_sayisi) * mahalle_yetiskin_nufus
            durumdan_etkilenen_yetiskin_nufus_orani = round((durumdan_etkilenen_yetiskin_nufus / mahalle_yetiskin_nufus) * 100,2)
            durumdan_etkilenen_yetiskin_nufus = k_model.etkilenen_nufus_predict(durumdan_etkilenen_yetiskin_nufus)
            toplam_genc_nufus += durumdan_etkilenen_genc_nufus
            toplam_genc_nufus_orani += durumdan_etkilenen_genc_nufus_orani 

            toplam_yetiskin_nufus += durumdan_etkilenen_yetiskin_nufus 
            toplam_yetiskin_nufus_orani += durumdan_etkilenen_yetiskin_nufus_orani






            

            #birincil_bolgedeki_binalar = []

            # (ikincil derece)
            try:
                genisletilmis_coords = ikincil_derece_alan(geojson, durum_katsayi)
                genisletilmis_veri = {"type": "Polygon", "coordinates": [genisletilmis_coords]}
                ikincil_bolgedeki_binalar = fetch_buildings_from_area(genisletilmis_veri)
                
            except:
                pass

            etkilenecek_binalar.append({
                "birincil_derece": birincil_bolgedeki_binalar, 
                "ikincil_derece": ikincil_bolgedeki_binalar,
            })
            #ikincil_bolgedeki_binalar = []

        # muhtemel etkilenecek yollar. 

        if yolanaliz:
            birincil_bolgedeki_yollar = ikincil_fetch_roads_from_area(geojson)
            etkilenecek_yollar.append({
                "birincil_derece": birincil_bolgedeki_yollar
            })


    ai_veri = { 
        "yasli_nufus":toplam_yetiskin_nufus,
        "yasli_nufus_orani":toplam_yetiskin_nufus_orani,
        "genc_nufus":toplam_genc_nufus,
        "genc_nufus_orani":toplam_genc_nufus_orani,
        "etkilenen_bina_sayisi": birincil_bolgedeki_bina_sayisi,
        "etkilenen_binalar":ozel_bina_listesi,
        "prompt": prompt
    }

    ai_answer = json.loads(aistdio.generate(ai_veri))
    #with open("ornek_cikti.json", "r") as file:
    #    ai_answer = json.loads(file.read())

    return {"etkilenecek_binalar": etkilenecek_binalar, "etkilenecek_yollar":etkilenecek_yollar, "mode":"area", "ai_response":ai_answer}



@app.route('/app')
def main_page():
    return render_template('app.html')


@app.route("/demo")
def test():
    return render_template("demo.html")


@app.route("/3d_test")
def ucdtest():
    return render_template("3d_test.html")

@app.route("/api", methods={"POST"})
def api():
    data = request.get_json()

    if len(data["areas"]) == 0:
        return_json = text_tabanli(data)
    else:
        return_json = bolge_tabanli(data)

    return return_json

if __name__ == '__main__':
    app.run(debug=True, host="localhost", port="5001")



