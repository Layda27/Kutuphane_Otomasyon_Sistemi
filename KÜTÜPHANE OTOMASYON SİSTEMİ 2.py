
"""
Created on Tue Dec  2 22:37:34 2025

@author: Neslihan Tuanna
"""

#NESNE TABANLI PROGRAMLAMA DÜZELTİLMİŞ HALİ
# kütüphane_otomasyon.py
from enum import Enum
from datetime import date, timedelta, datetime
import hashlib
import json
import os
from typing import Optional, Dict, Any, List
import re
from datetime import date, timedelta




KULLANICI_DOSYA = "kullanicilar.json"
KITAP_DOSYA = "kitaplar.json"
KITAPLAR: Dict[int, "Kitap"] = {}
KULLANICILAR: Dict[int, "Kullanici"] = {}
ISLEMLER: Dict[int, "Islem"] = {}
REZERVASYONLAR: Dict[int, "Rezervasyon"] = {}
KULLANICI_DOSYA = "kullanicilar.json"




class Kullanici:
    """Base kullanıcı sınıfı. Private: id, telefon, tc, sifre."""
    def __init__(self, kullaniciId: int, ad: str, soyad: str, telefon: str, email: str, sifre: Optional[str]=None):
      
        if not ad or not ad.strip() or not is_only_letters(ad):
            raise ValueError("Ad boş olamaz ve sadece harflerden oluşmalıdır.")
        if not soyad or not soyad.strip() or not is_only_letters(soyad):
            raise ValueError("Soyad boş olamaz ve sadece harflerden oluşmalıdır.")
        if not email or not email.strip():
            raise ValueError("Email boş olamaz.")
        if not is_valid_email(email):
            raise ValueError("Gecersiz email adresi.")

       
        self.__kullaniciId = kullaniciId
        self.ad = ad.strip()
        self.soyad = soyad.strip()
        self.__telefon = None
        self.setTelefon(telefon)
        self.email = email.strip()
        self.__sifre = None
        if sifre is not None:
            self.setSifre(sifre)
        self.__tc = None  

  


    def getId(self) -> int:
        return self.__kullaniciId

    def getTelefon(self) -> str:
        return self.__telefon

    def setTelefon(self, yeni: str):
        if not is_valid_phone(yeni):
           raise ValueError("Telefon 5 ile başlamalı ve 10 haneli olmalıdır.")
        self.__telefon = yeni

    def getTc(self) -> Optional[str]:
        return self.__tc

    def setTc(self, yeni: str):
        if len(yeni) != 11 or not yeni.isdigit():
            raise ValueError("TC 11 haneli olmalı ve sadece rakamlardan oluşmalıdır.")
        self.__tc = yeni

    def setSifre(self, sifre: str):
        if not sifre or not sifre.strip():
            raise ValueError("Şifre boş olamaz.")
       
        self.__sifre = hash_sha256(sifre.strip())
        
        
    def checkSifre(self, sifre: str) -> bool:
        if self.__sifre is None:
            return False
        return self.__sifre == hash_sha256(sifre)

   
    def girisYap(self, email: str, sifre: str) -> bool:
        return self.email == email and self.checkSifre(sifre)

    def cikisYap(self) -> bool:
        return True

    def profilGoruntule(self) -> Dict[str, Any]:
        return {
            "ID": self.getId(),
            "Ad": self.ad,
            "Soyad": self.soyad,
            "Telefon": self.getTelefon(),
            "Email": self.email,
            "TC": self.getTc()
        }

    def profilGuncelle(self, **bilgiler) -> str:
        for key, value in bilgiler.items():
            if key == "telefon":
                self.setTelefon(value)
            elif key == "tc":
                self.setTc(value)
            elif key == "sifre":
                self.setSifre(value)
            elif hasattr(self, key):
                setattr(self, key, value)
        return "Profil güncellendi."

class Uye(Kullanici):
    def __init__(self, kullaniciId: int, ad: str, soyad: str, telefon: str, email: str, sifre: str, cezaBakiyesi: float=0.0, puan: int=0):
        super().__init__(kullaniciId, ad, soyad, telefon, email, sifre)
        self.cezaBakiyesi = float(cezaBakiyesi)
        self.puan = int(puan)

    def kitapAra(self, kitapAdi: str):
        sonuc = [k for k in KITAPLAR.values() if kitapAdi.lower() in k.kitapAdi.lower()]
        return sonuc or "Kitap bulunamadı."

    def kitapOduncAl(self, kitapId: int, ayarlar: Optional["Ayarlar"]=None):

        limit = ayarlar.kullaniciKitapLimiti if ayarlar else 5
        aktif = sum(1 for i in ISLEMLER.values() if isinstance(i, OduncIslemi) and i.kullaniciId == self.getId())
        if aktif >= limit:
            return f"Kitap alma limitine ulaştınız (limit: {limit})."

        kitap = KITAPLAR.get(kitapId)
        if not kitap:
            return "Kitap bulunamadı."
        if kitap.mevcutAdet <= 0:
            
            return "Kitap stokta yok. Rezervasyon yapabilirsiniz."
       
        kitap.mevcutAdet -= 1
        yeni_id = max(ISLEMLER.keys(), default=0) + 1
        islem = OduncIslemi(
            islemId=yeni_id,
            kullaniciId=self.getId(),
            kitapId=kitapId,
            almaTarihi=date.today(),
            iadeTarihi=date.today() + timedelta(days=ayarlar.maxOduncGunSayisi if ayarlar else 14),
            cezaMiktari=0.0
        )
        ISLEMLER[islem.islemId] = islem
        return "Kitap başarıyla ödünç alındı."

    def kitapIadeEt(self, kitapId: int):
       
        for islem in list(ISLEMLER.values()):
            if isinstance(islem, OduncIslemi) and islem.kullaniciId == self.getId() and islem.kitapId == kitapId:
                islem.iadeEt()
                
                if islem.cezaMiktari > 0:
                    self.cezaBakiyesi += islem.cezaMiktari
               
                KITAPLAR[kitapId].mevcutAdet += 1
                
                del ISLEMLER[islem.islemId]
               
                rezervasyon_ver = None
                for rez in sorted(REZERVASYONLAR.values(), key=lambda r: r.rezervasyonTarihi):
                    if rez.kitapId == kitapId and rez.durum == Durum.REZERVE:
                        rezervasyon_ver = rez
                        break
                if rezervasyon_ver:
                    
                    rezervasyon_ver.durum = Durum.ODUNC_VERILDI
                   
                    yeni_id = max(ISLEMLER.keys(), default=0) + 1
                    yeni_islem = OduncIslemi(
                        islemId=yeni_id,
                        kullaniciId=rezervasyon_ver.kullaniciId,
                        kitapId=kitapId,
                        almaTarihi=date.today(),
                        iadeTarihi=date.today() + timedelta(days=14),
                        cezaMiktari=0.0
                    )
                    ISLEMLER[yeni_islem.islemId] = yeni_islem
                    KITAPLAR[kitapId].mevcutAdet -= 1
                return "İade işlemi tamamlandı."
        return "Bu kitap sizde kayıtlı değil."

    def cezaOde(self, miktar: float):
        if miktar > self.cezaBakiyesi:
            return "Ödenmek istenen miktar ceza bakiyesinden fazla."
        self.cezaBakiyesi -= miktar
        return "Ceza ödendi."

class Yonetici(Kullanici):
    def __init__(self, kullaniciId: int, ad: str, soyad: str, telefon: str, email: str, sifre: str,
                 kitapEkle: bool=True, kitapSil: bool=True, kitapGuncelle: bool=True,
                 kullaniciYonet: bool=True, ayarGuncelle: bool=True, raporOlustur: bool=True):
        super().__init__(kullaniciId, ad, soyad, telefon, email, sifre)
        self.kitapEkle = kitapEkle
        self.kitapSil = kitapSil
        self.kitapGuncelle = kitapGuncelle
        self.kullaniciYonet = kullaniciYonet
        self.ayarGuncelle = ayarGuncelle
        self.raporOlustur = raporOlustur

   
    def ekle_kitap(self, kitap: "Kitap"):
        if not self.kitapEkle:
            raise PermissionError("Bu yönetici kitap ekleyemez.")
        if kitap.kitapId in KITAPLAR:
            raise ValueError("Bu ID ile kitap zaten var.")
        KITAPLAR[kitap.kitapId] = kitap
        return "Kitap eklendi."

    def sil_kitap(self, kitapId: int):
        if not self.kitapSil:
            raise PermissionError("Bu yönetici kitap silemez.")
        if kitapId not in KITAPLAR:
            return "Kitap bulunamadı."
        del KITAPLAR[kitapId]
        return "Kitap silindi."

    def guncelle_kitap(self, kitapId: int, **bilgiler):
        if not self.kitapGuncelle:
            raise PermissionError("Bu yönetici kitap güncelleyemez.")
        kitap = KITAPLAR.get(kitapId)
        if not kitap:
            return "Kitap bulunamadı."
        kitap.bilgiGuncelle(**bilgiler)
        return "Kitap güncellendi."

    def ekle_uye(self, uye: Uye):
        if not self.kullaniciYonet:
            raise PermissionError("Bu yönetici üye ekleyemez.")
        if uye.getId() in KULLANICILAR:
            raise ValueError("Bu ID ile üye zaten var.")
        KULLANICILAR[uye.getId()] = uye
        return "Üye eklendi."

    def sil_uye(self, uyeId: int):
        if not self.kullaniciYonet:
            raise PermissionError("Bu yönetici üye silemez.")
        if uyeId not in KULLANICILAR:
            return "Üye bulunamadı."
        del KULLANICILAR[uyeId]
        return "Üye silindi."

class Islem:
    def __init__(self, islemId: int, kullaniciId: int, kitapId: int):
        self.islemId = islemId
        self.kullaniciId = kullaniciId
        self.kitapId = kitapId
        self.tarih = date.today()

    def islemKaydet(self):  
        ISLEMLER[self.islemId] = self
        return "İşlem kaydedildi."

    def islemTarihi(self):
        return self.tarih

    def islemSil(self):
        if self.islemId in ISLEMLER:
            del ISLEMLER[self.islemId]
            return "İşlem silindi."
        return "İşlem bulunamadı."

    def islemDetayGoruntule(self):
        return vars(self)
    
    def to_dict(self):
      return {
        "islemId": self.islemId,
        "kullaniciId": self.kullaniciId,
        "kitapId": self.kitapId,
        "tarih": str(self.tarih)
    }


class OduncIslemi(Islem):
    def __init__(self, islemId: int, kullaniciId: int, kitapId: int, almaTarihi: date, iadeTarihi: date, cezaMiktari: float=0.0):
        super().__init__(islemId, kullaniciId, kitapId)
        self.almaTarihi = almaTarihi
        self.iadeTarihi = iadeTarihi
        self.cezaMiktari = float(cezaMiktari)

    def oduncAl(self):
        return self.islemKaydet()

    def iadeEt(self):
         gecikme = (date.today() - self.iadeTarihi).days
            
         if gecikme > 0:
             self.cezaMiktari = gecikme * AYARLAR.cezaGunlukMiktar
             self.durum = Durum.GECIKMIS
         else:
             self.cezaMiktari = 0.0
             self.durum = Durum.MUSAIT



    def cezaHesapla(self):
        gecikme = (date.today() - self.iadeTarihi).days
        return max(0, gecikme * 5.0)

    def oduncDurumuKontrolEt(self):
        return "Gecikmiş" if date.today() > self.iadeTarihi else "Zamanında"
    
    def to_dict(self):
        data = super().to_dict()
        data.update({
            "almaTarihi": str(self.almaTarihi),
            "iadeTarihi": str(self.iadeTarihi),
            "cezaMiktari": self.cezaMiktari
        })
        return data


class Rezervasyon(Islem):
    def __init__(self, islemId: int, kullaniciId: int, kitapId: int, rezervasyonId: int, rezervasyonTarihi: date, durum: "Durum"):
        super().__init__(islemId, kullaniciId, kitapId)
        self.rezervasyonId = rezervasyonId
        self.rezervasyonTarihi = rezervasyonTarihi
        self.durum = durum

    def rezervasyonYap(self):
        for r in REZERVASYONLAR.values():
            if r.kitapId == self.kitapId and r.durum == Durum.REZERVE:
                return "Bu kitap zaten rezerve edilmiş."
    
        REZERVASYONLAR[self.rezervasyonId] = self
        self.durum = Durum.REZERVE
        return "Rezervasyon yapıldı."


    def rezervasyonIptalEt(self):
        if self.rezervasyonId in REZERVASYONLAR:
            del REZERVASYONLAR[self.rezervasyonId]
        self.durum = Durum.IPTAL
        return "Rezervasyon iptal edildi."



    def durumGuncelle(self, yeniDurum: "Durum"):
        self.durum = yeniDurum
        return "Durum güncellendi."
    
    def to_dict(self):
        data = super().to_dict()
        data.update({
            "rezervasyonId": self.rezervasyonId,
            "rezervasyonTarihi": str(self.rezervasyonTarihi),
            "durum": self.durum.name
        })
        return data


class Ayarlar:
    
    
    DOSYA_ADI = "ayarlar.json"

    def __init__(
        self,
        maxOduncGunSayisi: int = 14,
        cezaGunlukMiktar: float = 5.0,
        kullaniciKitapLimiti: int = 5
    ):
        self.maxOduncGunSayisi = maxOduncGunSayisi
        self.cezaGunlukMiktar = cezaGunlukMiktar
        self.kullaniciKitapLimiti = kullaniciKitapLimiti


    def to_dict(self):
        return {
            "maxOduncGunSayisi": self.maxOduncGunSayisi,
            "cezaGunlukMiktar": self.cezaGunlukMiktar,
            "kullaniciKitapLimiti": self.kullaniciKitapLimiti
        }

    
    def kaydet(self):
        with open(self.DOSYA_ADI, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        return "Ayarlar kaydedildi."

    
    def yukle(self):
        if not os.path.exists(self.DOSYA_ADI):
            return "Ayar dosyası yok, varsayılan ayarlar kullanılıyor."

        with open(self.DOSYA_ADI, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.maxOduncGunSayisi = data.get("maxOduncGunSayisi", self.maxOduncGunSayisi)
        self.cezaGunlukMiktar = data.get("cezaGunlukMiktar", self.cezaGunlukMiktar)
        self.kullaniciKitapLimiti = data.get("kullaniciKitapLimiti", self.kullaniciKitapLimiti)

        return "Ayarlar yüklendi."


    def ayarGuncelle(self, **yeni):
        for k, v in yeni.items():
            if hasattr(self, k):
                setattr(self, k, v)
        self.kaydet()
        return "Ayarlar güncellendi."
    
AYARLAR = Ayarlar()
AYARLAR.yukle()








class Kitap:
    def __init__(self, kitapId, kitapAdi, yazar, yayinevi, tur, ISBN, toplamAdet, mevcutAdet):
      
        if not kitapAdi.strip():
            raise ValueError("Kitap adi bos olamaz.")
        if toplamAdet < 0 or mevcutAdet < 0:
            raise ValueError("Adetler negatif olamaz.")
        if mevcutAdet > toplamAdet:
            raise ValueError("Mevcut adet toplam adetten fazla olamaz.")

        self.kitapId = kitapId
        self.kitapAdi = kitapAdi.strip()
        self.yazar = yazar.strip()
        self.yayinevi = yayinevi.strip()
        self.tur = tur.strip()
        self.ISBN = ISBN.strip()
        self.toplamAdet = toplamAdet
        self.mevcutAdet = mevcutAdet
        
        def durum(self):
            if self.mevcutAdet > 0:
                return "Musait"
            return "Stokta Yok"


    def to_dict(self):
        return {
            "kitapId": self.kitapId,
            "kitapAdi": self.kitapAdi,
            "yazar": self.yazar,
            "yayinevi": self.yayinevi,
            "tur": self.tur,
            "ISBN": self.ISBN,
            "toplamAdet": self.toplamAdet,
            "mevcutAdet": self.mevcutAdet
        }
    
    def bilgiGuncelle(self, **bilgiler):
      for k, v in bilgiler.items():
        if hasattr(self, k):
            setattr(self, k, v)

    @staticmethod
    def from_dict(data):
        return Kitap(
            data["kitapId"],
            data["kitapAdi"],
            data["yazar"],
            data["yayinevi"],
            data["tur"],
            data["ISBN"],
            data["toplamAdet"],
            data["mevcutAdet"]
        )
    def detayGoster(self):
       return (
        f"ID: {self.kitapId}\n"
        f"Ad: {self.kitapAdi}\n"
        f"Yazar: {self.yazar}\n"
        f"Yayinevi: {self.yayinevi}\n"
        f"Tur: {self.tur}\n"
        f"ISBN: {self.ISBN}\n"
        f"Toplam Adet: {self.toplamAdet}\n"
        f"Mevcut Adet: {self.mevcutAdet}\n"
        f"Durum: {self.durum()}"
    )
   







class Durum(Enum):
    MUSAIT = 1           
    ODUNC_VERILDI = 2    
    REZERVE = 3          
    GECIKMIS = 4         
    IPTAL = 5            


class Raporlama:
    def __init__(self, raporTarihi: date):
        self.raporTarihi = raporTarihi
        self.olusturulanRaporlar = []

    def enCokOkunanlar(self) -> List:
        sayac = {}
        for islem in ISLEMLER.values():
            if isinstance(islem, OduncIslemi):
              sayac[islem.kitapId] = sayac.get(islem.kitapId, 0) + 1

        return sorted(sayac.items(), key=lambda x: x[1], reverse=True)

    def enAktifUyeler(self) -> List:
        sayac = {}
        for islem in ISLEMLER.values():
           if isinstance(islem, OduncIslemi):
              sayac[islem.kitapId] = sayac.get(islem.kitapId, 0) + 1

        return sorted(sayac.items(), key=lambda x: x[1], reverse=True)

    def gecikmeYapanlar(self) -> List:
        geciken = set()
        


        for islem in ISLEMLER.values():
            if isinstance(islem, OduncIslemi) and date.today() > islem.iadeTarihi:
                geciken.append(islem.kullaniciId)
        return list(geciken)

  
    def kaydet_en_cok_okunanlar(self):
        veri = [{"kitapId": k, "say": s} for k, s in self.enCokOkunanlar()]
        return self.raporKaydet("en_cok_okunanlar", veri)


    def kaydet_en_aktif_uyeler(self):
        veri = [{"kitapId": k, "say": s} for k, s in self.enAktifUyeler()]
        return self.raporKaydet("en_aktif_uyeler", veri)

    
    def raporKaydet(self, raporAdi: str, veri: list):
        dosya = f"{raporAdi}.json"
        with open(dosya, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "tarih": str(self.raporTarihi),
                    "rapor": raporAdi,
                    "veri": veri
                },
                f,
                ensure_ascii=False,
                indent=2
            )
        self.olusturulanRaporlar.append(raporAdi)
        return dosya


class Konum:
    def __init__(self, rafNo: str, koridor: str, kat: str):
        self.rafNo = rafNo
        self.koridor = koridor
        self.kat = kat

    def konumGoster(self) -> str:
        return f"Kat: {self.kat}, Koridor: {self.koridor}, Raf: {self.rafNo}"


    def to_dict(self) -> dict:
        return {
            "kat": self.kat,
            "koridor": self.koridor,
            "rafNo": self.rafNo
        }


class CezaYonetimi:
    def __init__(self, cezaKayitlari: Optional[Dict[int, float]]=None, gunlukCeza: float=5.0):
        self.cezaKayitlari = cezaKayitlari if cezaKayitlari is not None else {}
        self.gunlukCeza = float(gunlukCeza)

    def cezaHesapla(self, gecikenGun: int, uyeId: Optional[int]=None, kitapId: Optional[int]=None) -> float:
        return gecikenGun * self.gunlukCeza

    def cezaEkle(self, uyeId: int, ceza: float) -> str:
        self.cezaKayitlari[uyeId] = self.cezaKayitlari.get(uyeId, 0.0) + float(ceza)
        return "Ceza eklendi."

    def cezaRaporuOlustur(self) -> Dict[int, float]:
        return self.cezaKayitlari

    
    def gunluk_ceza_kontrol(self) -> List[Dict[str, Any]]:
        uygulanan = []
        for islem in list(ISLEMLER.values()):
            if isinstance(islem, OduncIslemi):
                if date.today() > islem.iadeTarihi:
                    gecikme = (date.today() - islem.iadeTarihi).days
                    ceza = self.cezaHesapla(gecikme)
                    
                    uye = KULLANICILAR.get(islem.kullaniciId)
                    if isinstance(uye, Uye):
                        uye.cezaBakiyesi += ceza
                        self.cezaKayitlari[islem.kullaniciId] = self.cezaKayitlari.get(islem.kullaniciId, 0.0) + ceza
                        uygulanan.append({"islemId": islem.islemId, "kullaniciId": islem.kullaniciId, "ceza": ceza})
        return uygulanan

def is_valid_phone(phone: str) -> bool:
    
     return bool(re.fullmatch(r"5\d{9}", phone))


def is_valid_email(email: str) -> bool:
    
    allowed_domains = ("gmail.com", "hotmail.com", "icloud.com")
    if "@" not in email:
        return False
    local, domain = email.split("@", 1)
    return bool(local) and domain in allowed_domains

def kitaplari_listele():
    print("\n--- KITAPLAR ---")
    if not KITAPLAR:
        print("Hic kitap bulunamadi!")
        return
    for k in KITAPLAR.values():
        print(
            f"ID: {k.kitapId} | "
            f"Adi: {k.kitapAdi} | "
            f"Yazar: {k.yazar} | "
            f"Yayınevi: {k.yayinevi} | "
            f"Tur: {k.tur} | "
            f"ISBN: {k.ISBN} | "
            f"Toplam: {k.toplamAdet} | "
            f"Mevcut: {k.mevcutAdet}"
        )
def kitaplari_kaydet():
    with open("kitaplar.json", "w", encoding="utf-8") as f:
        json.dump(
            {kitap_id: kitap.to_dict() for kitap_id, kitap in KITAPLAR.items()},
            f,
            ensure_ascii=False,
            indent=4
        )

        
        
def ad_soyad_input(mesaj: str) -> str:
    while True:
        deger = input(mesaj).strip()

        if not deger:
            print(" Boş bırakılamaz.")
            continue

        if len(deger) > 40:
            print(" En fazla 40 karakter girebilirsiniz.")
            continue

        if not deger.replace(" ", "").isalpha():
            print(" Sadece harf ve boşluk kullanılabilir.")
            continue

        return deger







def kullanicilari_kaydet():
    data = []
    for k in KULLANICILAR.values():
        data.append({
            "tip": k.__class__.__name__,
            "id": k.getId(),
            "ad": k.ad,
            "soyad": k.soyad,
            "telefon": k.getTelefon(),
            "email": k.email,
            "_sifre": k._Kullanici__sifre,
            "ceza": getattr(k, "cezaBakiyesi", 0.0),
            "puan": getattr(k, "puan", 0)
        })
    with open(KULLANICI_DOSYA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def kullanicilari_yukle():
    if not os.path.exists(KULLANICI_DOSYA):
        return

    with open(KULLANICI_DOSYA, "r", encoding="utf-8") as f:
        data = json.load(f)

    for k in data:
        if k["tip"] == "Uye":
            uye = Uye(
                k["id"], k["ad"], k["soyad"],
                k["telefon"], k["email"], "temp"
            )
            uye._Kullanici__sifre = k["_sifre"]
            uye.cezaBakiyesi = k["ceza"]
            uye.puan = k["puan"]
            KULLANICILAR[uye.getId()] = uye

        elif k["tip"] == "Yonetici":
            admin = Yonetici(
                k["id"], k["ad"], k["soyad"],
                k["telefon"], k["email"], "temp"
            )
            admin._Kullanici__sifre = k["_sifre"]
            KULLANICILAR[admin.getId()] = admin
            
            
def kitaplari_yukle():
    global KITAPLAR
    if not os.path.exists("kitaplar.json"):
        KITAPLAR = {}
        return

    with open("kitaplar.json", "r", encoding="utf-8") as dosya:
        veriler = json.load(dosya)

    for kitap_id, kitap_bilgisi in veriler.items():
        
        kitap = Kitap.from_dict(kitap_bilgisi)
        KITAPLAR[int(kitap_id)] = kitap



            
def yeni_id_uret(sozluk):
    return max(sozluk.keys(), default=0) + 1



"""
buraya tekrar bak
"""
def hash_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def is_only_letters(s: str) -> bool:
    return s.replace(" ", "").isalpha()

def ensure_dir(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None



def uye_ekle(admin: Yonetici):
    try:
        uye_id = yeni_id_uret(KULLANICILAR)

        uye = Uye(
            uye_id,
            ad_soyad_input("Ad: "),
            ad_soyad_input("Soyad: "),
            input("Telefon: "),
            input("Email: "),
            input("Sifre: ")
        )

        print(admin.ekle_uye(uye))
        kullanicilari_kaydet()

    except Exception as e:
        print("Hata:", e)



def uye_sil(admin: Yonetici):
    try:
        uid = int(input("Silinecek uye ID: "))
        print(admin.sil_uye(uid))
        kullanicilari_kaydet()
    except Exception as e:
        print("Hata:", e)
        
        


def kitap_ekle(admin: Yonetici):
    try:
        kitap_id = yeni_id_uret(KITAPLAR)

        kitap = Kitap(
            kitap_id,
            input("Kitap Adı: "),
            input("Yazar: "),
            input("Yayınevi: "),
            input("Tür: "),
            input("ISBN: "),
            int(input("Toplam Adet: ")),
            int(input("Mevcut Adet: "))
        )

        print(admin.ekle_kitap(kitap))
        kitaplari_kaydet()

    except Exception as e:
        print("Hata:", e)


        


def kitap_guncelle(admin: Yonetici):
    try:
        kid = int(input("Kitap ID: "))
        alan = input("Güncellenecek alan: ")
        deger = input("Yeni değer: ")
        print(admin.guncelle_kitap(kid, **{alan: deger}))
        kitaplari_kaydet()
    except Exception as e:
        print("Hata:", e)

def kitap_sil(admin: Yonetici):
    try:
        kid = int(input("Kitap ID: "))
        print(admin.sil_kitap(kid))
        kitaplari_kaydet()
    except Exception as e:
        print("Hata:", e)
        

def admin_menu(admin: Yonetici):
    global KULLANICILAR, KITAPLAR, ISLEMLER 
    while True:
        print("\n--- ADMIN PANELI ---")
        print("1- Uye Ekle")
        print("2- Uye Sil")
        print("3- Kitap Ekle")
        print("4- Kitap Guncelle")
        print("5- Kitap Sil")
        print("6- Uyeleri Listele")
        print("7- Kitaplari Listele")
        print("8- Raporlari Goruntule")
        print("9- Ayarlari Goruntule / Guncelle")
        print("0- Cikis")

        secim = input("Secim: ")

        if secim == "1":
            uye_ekle(admin)
        elif secim == "2":
            uye_sil(admin)
        elif secim == "3":
            kitap_ekle(admin)
        elif secim == "4":
            kitap_guncelle(admin)
        elif secim == "5":
            kitap_sil(admin)
        elif secim == "6":
            uyeleri_listele()
        elif secim == "7":
            kitaplari_listele()
        elif secim == "8":
            rapor = Raporlama(date.today())
            rapor.kaydet_en_cok_okunanlar()
            rapor.kaydet_en_aktif_uyeler()
            print("Raporlar JSON dosyasina kaydedildi.")

            print("\n--- EN COK OKUNAN KITAPLAR ---")
            for kitapId, sayi in rapor.enCokOkunanlar():
                kitap = KITAPLAR.get(kitapId)
                if kitap:
                    print(f"{kitap.kitapAdi} ({kitap.yazar}) -> {sayi} kez")

            print("\n--- EN AKTIF UYELER ---")
            for uyeId, sayi in rapor.enAktifUyeler():
                uye = KULLANICILAR.get(uyeId)
                if uye:
                    print(f"{uye.ad} {uye.soyad} -> {sayi} kitap")

            print("\n--- GECIKME YAPAN UYELER ---")
            gecikenler = rapor.gecikmeYapanlar()
            if not gecikenler:
                print("Gecikme yapan uye yok.")
                
        
            else:
                for uyeId in set(gecikenler):
                    uye = KULLANICILAR.get(uyeId)
                    if uye:
                        print(f"{uye.ad} {uye.soyad}")
                        
        elif secim == "9":
            ayarlar_menu(admin)


        elif secim == "0":
            break
        else:
            print("Gecersiz secim")
            
def uyeleri_listele():
    print("\n--- UYE LISTESI ---")
    bulundu = False

    for k in KULLANICILAR.values():
        if type(k) is Uye:
            bulundu = True
            print(
                f"ID: {k.getId()} | "
                f"Ad Soyad: {k.ad} {k.soyad} | "
                f"Email: {k.email} | "
                f"Ceza: {k.cezaBakiyesi}"
            )

    if not bulundu:
        print("Hic uye bulunamadi!")
        

def uye_menu(uye: Uye):
    while True:
        print("\n--- UYE MENU ---")
        print("1- Kitap Ara")
        print("2- Kitap Odunc Al")
        print("3- Kitap Iade Et")
        print("4- Ceza Goruntule")
        print("5- Ceza Ode")
        print("6- Profil Goruntule")
        print("7- Kitaplari Listele")  
        print("8- Kitap Detay Goruntule")


        print("0- Cikis")

        secim = input("Secim: ")

        if secim == "1":
            ad = input("Kitap adi: ")
            sonuc = uye.kitapAra(ad)
            print(sonuc)

        elif secim == "2":
           kitapId = int(input("Kitap ID: "))
           print(uye.kitapOduncAl(kitapId, AYARLAR))

           
           
           uye = next(
        (k for k in KULLANICILAR.values()
         if isinstance(k, Uye) and k.girisYap(email, sifre)),
        None
    )
           if uye:
               print(f"Hoşgeldin, {uye.ad}!")
               uye_menu(uye)
           else:
               print("Uye girisi hatali! Ana menuye dönülüyor...")




        elif secim == "3":
            kid = int(input("Kitap ID: "))
            print(uye.kitapIadeEt(kid))

        elif secim == "4":
            print("Ceza Bakiyesi:", uye.cezaBakiyesi)

        elif secim == "5":
            miktar = float(input("Odenecek miktar: "))
            print(uye.cezaOde(miktar))

        elif secim == "6":
            print(uye.profilGoruntule())
            
        elif secim == "7":
             kitaplari_listele()
             
        elif secim == "8":
            kid = int(input("Kitap ID: "))
            kitap = KITAPLAR.get(kid)
            if kitap:
                print(kitap.detayGoster())
            else:
                print("Kitap bulunamadi.")



        elif secim == "0":
            break

        else:
            print("Gecersiz secim")
            
def uye_kayit():
  print("\n--- UYE KAYIT ---")

  try:
      kullaniciId = yeni_id_uret(KULLANICILAR)

      ad = ad_soyad_input("Ad: ")
      soyad = ad_soyad_input("Soyad: ")
      telefon = input("Telefon (5xxxxxxxxx): ")
      email = input("Email: ")
      sifre = input("Sifre: ")

      uye = Uye(kullaniciId, ad, soyad, telefon, email, sifre)
      KULLANICILAR[uye.getId()] = uye

      kullanicilari_kaydet()
      print("Kayit basarili!")

  except Exception as e:
      print("Hata:", e)
            
def uye_giris():
    email = input("Uye Email: ")
    sifre = input("Uye Sifre: ")

   
    uye = next(
        (k for k in KULLANICILAR.values() 
         if isinstance(k, Uye) and k.girisYap(email, sifre)),
        None
    )

    if uye:
        print(f"Hoşgeldiniz, {uye.ad}!")
        uye_menu(uye)  
    else:
        print("Uye girisi hatali! Ana menuye dönülüyor...")
        
        
def ayarlar_menu(admin: Yonetici):
    if not admin.ayarGuncelle:
        print("Bu admin ayarlari guncelleyemez.")
        return

    while True:
        print("\n--- AYARLAR ---")
        print(f"1- Max Odunc Gun Sayisi: {AYARLAR.maxOduncGunSayisi}")
        print(f"2- Gunluk Ceza Miktari: {AYARLAR.cezaGunlukMiktar}")
        print(f"3- Kullanici Kitap Limiti: {AYARLAR.kullaniciKitapLimiti}")
        print("0- Geri Don")

        secim = input("Secim: ")

        if secim == "1":
            AYARLAR.maxOduncGunSayisi = int(input("Yeni max gun: "))
        elif secim == "2":
            AYARLAR.cezaGunlukMiktar = float(input("Yeni gunluk ceza: "))
        elif secim == "3":
            AYARLAR.kullaniciKitapLimiti = int(input("Yeni kitap limiti: "))
        elif secim == "0":
            AYARLAR.kaydet()
            print("Ayarlar kaydedildi.")
            break
        else:
            print("Gecersiz secim!")

        


if __name__ == "__main__":

    
    kullanicilari_yukle()
    kitaplari_yukle()

   
    if 1 not in KULLANICILAR:
        admin = Yonetici(
            1,
            "Admin",
            "User",
            "5555555555",
            "admin@gmail.com",
            "Admin1234"
        )
        KULLANICILAR[admin.getId()] = admin
        kullanicilari_kaydet()
    else:
        admin = KULLANICILAR[1]

    
    while True:
        print("\n--- KUTUPHANE OTOMASYON SISTEMI ---")
        print("1- Admin Girisi")
        print("2- Uye Girisi")
        print("3- Uye Kayit")
        print("0- Cikis")

        secim = input("Secim: ")

        if secim == "0":
            print("Programdan cikiliyor...")
            break

        elif secim == "1":
            email = input("Admin Email: ")
            sifre = input("Admin Sifre: ")

            if admin.girisYap(email, sifre):
                admin_menu(admin)
            else:
                print("Admin girisi hatali!")

        elif secim == "2":
            uye_giris()

        elif secim == "3":
            uye_kayit()

        else:
            print("Gecersiz secim!")

        
        





