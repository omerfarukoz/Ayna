import requests

def get_coordinates(adres):
    url = "https://nominatim.openstreetmap.org/search"

    params = {
        'q': adres,
        'format': 'json'
    }

    response = requests.get(url, params=params, headers={'User-Agent': 'Mozilla/5.0'})
    data = response.json()

    if data:
        lat = data[0]['lat']
        lon = data[0]['lon']
        print(f"Koordinatlar: {lat}, {lon}")
    else:
        print("Adres bulunamadı.")
