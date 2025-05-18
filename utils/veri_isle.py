import json
with open("mahalle.csv", "r") as file:
    csv_file_rows = file.read().split("\n")[5:]

nufus_veri = {}
toplam_nufus = 0
for row in csv_file_rows:
    try:
        row_l = row.split("|")
        print(row_l)
        mahalle = row_l[1].split(")")[0].split("/")[-1].split(" ")[0].lower()
        eksi_onsekiz = int(float(row_l[2]))
        arti_onsekiz = int(float(row_l[3]))
        toplam_nufus = eksi_onsekiz + arti_onsekiz

        ortalama_hane_sayisi = int((eksi_onsekiz + arti_onsekiz) / 3.24)

        toplam_nufus += eksi_onsekiz + arti_onsekiz 
        nufus_veri[mahalle] = {"eski_onsekiz": eksi_onsekiz, "arti_onsekiz": arti_onsekiz,"toplam_nufus":toplam_nufus, "ortalama_hane": ortalama_hane_sayisi}
    except:
        pass

#nufus_veri["toplam_nufus"] = toplam_nufus
#nufus_veri["bina_sayisi"] = int(toplam_nufus / 3.24)
with open("nufus_veri.json","w") as json_file:
    json_file.write(json.dumps(nufus_veri))


