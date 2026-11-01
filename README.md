# AtsFlow

Yerel ag (LAN) uzerinde muzik ve dosya paylasimi + internetten muzik arama ve indirme.

## Ozellikler

- **Es keşfi**: UDP broadcast ile ayni agdaki AtsFlow bilgisayarlarini otomatik bulur
- **Dosya paylasimi**: `shared` klasorunuzdeki dosyalar agdaki tum cihazlara acilir
- **Muzik oynatici**: tarayici icinde sarma, ses, siradaki otomatik (playlist) desteği, video icin yuzen pencere
- **Internetten muzik**: YouTube arama, indirmeden canli onizleme, MP3 (192kbps) / MP4 (1080p) indirme
- **Arayuz**: web tarayici + masaustu penceresi (tkinter)
- **Kurulsuz**: tek dosya exe, hicbir bagimlilik gerektirmez

## Calistirma

Kaynaktan:

```
pip install yt-dlp imageio-ffmpeg
python main.py
```

Secenekler:

```
python main.py --dir D:\Muzik --port 9000 --no-gui --no-browser
```

## Windows paketi

```
powershell -ExecutionPolicy Bypass -File build_windows.ps1
```

Cikti: `dist\AtsFlow.exe` (tek dosya, ffmpeg dahil).

## Mimari

| Dosya | Gorev |
|---|---|
| `main.py` | giris noktasi, ayarlar |
| `core.py` | HTTP sunucu (indirme/akış/oynatma API'leri) + UDP es keşfi |
| `music.py` | yt-dlp ile arama, onizleme cozumleme, indirme yoneticisi |
| `gui.py` | masaustu kontrol penceresi |
| `web/` | tarayici arayuzu |
| `assets/` | logo ve ikonlar |
| `packaging/` | Microsoft Store (MSIX) bildirimi |

## Notlar

- Indirilen iceriklerin telif haklarina dikkat edin; paylasim sorumlulugu kullaniciya aittir.
- Dosya alisverisi yalnizca yerel ag icindedir; internete acik degildir.
