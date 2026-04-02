import os, io
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.core.image import Image as CoreImage
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from kivy.uix.scatter import Scatter

DERSLER_PATH = '/storage/emulated/0/DERSLERİM'

def get_dirs(yol):
    try: return sorted([f for f in os.listdir(yol) if os.path.isdir(os.path.join(yol, f))])
    except: return []

def get_pdfs(yol):
    try: return sorted([f for f in os.listdir(yol) if f.lower().endswith('.pdf')])
    except: return []

def ust_bar(baslik, geri_func=None):
    bar = BoxLayout(size_hint_y=None, height=dp(56), padding=[dp(10), dp(8)], spacing=dp(10))
    with bar.canvas.before:
        Color(0.2, 0.5, 0.8, 1)
        rect = Rectangle(pos=bar.pos, size=bar.size)
    bar.bind(pos=lambda *a: setattr(rect, 'pos', bar.pos))
    bar.bind(size=lambda *a: setattr(rect, 'size', bar.size))
    if geri_func:
        geri = Button(text='< Geri', size_hint_x=None, width=dp(90), background_color=(0.1, 0.4, 0.7, 1), font_size=dp(16))
        geri.bind(on_press=lambda x: geri_func())
        bar.add_widget(geri)
    bar.add_widget(Label(text=baslik, font_size=dp(17), bold=True))
    return bar

def liste_btn(metin, callback):
    btn = Button(text=metin, size_hint_y=None, height=dp(65), font_size=dp(15), halign='left', padding_x=dp(15), background_color=(0.15, 0.15, 0.15, 1), background_normal='')
    btn.bind(on_press=lambda x: callback())
    return btn

class PDFRenderer:
    def __init__(self, pdf_yol):
        from jnius import autoclass
        self.PdfRenderer = autoclass('android.graphics.pdf.PdfRenderer')
        self.ParcelFileDescriptor = autoclass('android.os.ParcelFileDescriptor')
        self.File = autoclass('java.io.File')
        self.Bitmap = autoclass('android.graphics.Bitmap')
        self.BitmapConfig = autoclass('android.graphics.Bitmap$Config')
        self.Canvas = autoclass('android.graphics.Canvas')
        self.PaintColor = autoclass('android.graphics.Color')
        self.ByteArrayOutputStream = autoclass('java.io.ByteArrayOutputStream')
        self.CompressFormat = autoclass('android.graphics.Bitmap$CompressFormat')

        f = self.File(pdf_yol)
        self.pfd = self.ParcelFileDescriptor.open(f, self.ParcelFileDescriptor.MODE_READ_ONLY)
        self.renderer = self.PdfRenderer(self.pfd)
        self.sayfa_sayisi = self.renderer.getPageCount()

    def sayfa_render(self, sayfa_no, zoom=2.0):
        bitmap = None
        out = None
        try:
            sayfa = self.renderer.openPage(sayfa_no)
            w = int(sayfa.getWidth() * zoom)
            h = int(sayfa.getHeight() * zoom)
            
            bitmap = self.Bitmap.createBitmap(w, h, self.BitmapConfig.ARGB_8888)
            canvas = self.Canvas(bitmap)
            canvas.drawColor(self.PaintColor.WHITE)
            sayfa.render(bitmap, None, None, 1)
            sayfa.close()
            
            out = self.ByteArrayOutputStream()
            bitmap.compress(self.CompressFormat.PNG, 90, out)
            buf = io.BytesIO(bytes(out.toByteArray()))
            return buf
        finally:
            if bitmap:
                try: bitmap.recycle()
                except: pass
            if out:
                try: out.close()
                except: pass

    def kapat(self):
        try:
            self.renderer.close()
            self.pfd.close()
        except: pass

class PDFEkrani(Screen):
    def __init__(self, pdf_yol, geri_func, **kwargs):
        super().__init__(**kwargs)
        self.pdf_yol = pdf_yol
        self.geri_func = geri_func
        self.pdf_renderer = None
        self.mevcut_sayfa = 0
        self.islem_yapiyor = False
        
        self.layout = BoxLayout(orientation='vertical')
        baslik = os.path.basename(pdf_yol)[:-4]
        self.layout.add_widget(ust_bar(baslik, self.geri_git))
        
        # Kapak Alanı
        self.goruntu_alani = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(20))
        self.layout.add_widget(self.goruntu_alani)
        
        # Alt Sayfalama Barı
        self.alt_bar = BoxLayout(size_hint_y=None, height=dp(60), padding=dp(5), spacing=dp(10))
        with self.alt_bar.canvas.before:
            Color(0.1, 0.1, 0.1, 1)
            self.alt_rect = Rectangle(pos=self.alt_bar.pos, size=self.alt_bar.size)
        self.alt_bar.bind(pos=lambda *a: setattr(self.alt_rect, 'pos', self.alt_bar.pos))
        self.alt_bar.bind(size=lambda *a: setattr(self.alt_rect, 'size', self.alt_bar.size))
        
        self.btn_onceki = Button(text='<< ONCEKI', font_size=dp(14), background_color=(0.2, 0.5, 0.8, 1))
        self.btn_onceki.bind(on_press=self.onceki_sayfa)
        
        self.lbl_sayfa = Label(text='-', bold=True)
        
        self.btn_sonraki = Button(text='SONRAKI >>', font_size=dp(14), background_color=(0.2, 0.5, 0.8, 1))
        self.btn_sonraki.bind(on_press=self.sonraki_sayfa)
        
        self.alt_bar.add_widget(self.btn_onceki)
        self.alt_bar.add_widget(self.lbl_sayfa)
        self.alt_bar.add_widget(self.btn_sonraki)
        
        self.add_widget(self.layout)

    def on_enter(self):
        # Ekrana girer girmez motoru ÇALIŞTIRMIYORUZ. Sadece başlat butonunu koyuyoruz.
        self.goruntu_alani.clear_widgets()
        
        uyari_lbl = Label(text="Dokunmatik çökmesini önlemek için\nlütfen aşağıdaki butona basın.", halign='center', color=(0.7,0.7,0.7,1))
        
        self.btn_baslat = Button(
            text="KİTABI YÜKLE VE AÇ", 
            font_size=dp(20), bold=True,
            size_hint=(1, None), height=dp(100),
            background_color=(0.1, 0.6, 0.2, 1)
        )
        self.btn_baslat.bind(on_press=self.manuel_tetikleyici)
        
        bosluk = BoxLayout() # Ortalamak için
        self.goruntu_alani.add_widget(uyari_lbl)
        self.goruntu_alani.add_widget(self.btn_baslat)
        self.goruntu_alani.add_widget(bosluk)

    def manuel_tetikleyici(self, instance):
        # Butona basıldı. Butonu kilitliyoruz.
        self.btn_baslat.disabled = True
        self.btn_baslat.text = "Motor Isınıyor...\nLütfen Bekleyin"
        self.btn_baslat.background_color = (0.5, 0.5, 0.5, 1)
        
        # HAYAT KURTARAN NOKTA: Parmağın ekrandan tam kalkması ve 
        # Android'in bunu algılaması için 0.6 saniye bekliyoruz.
        Clock.schedule_once(self.motoru_kur, 0.6)

    def motoru_kur(self, dt):
        try:
            self.pdf_renderer = PDFRenderer(self.pdf_yol)
            self.layout.add_widget(self.alt_bar) # Alt barı şimdi gösteriyoruz
            self.sayfa_hazirla(self.mevcut_sayfa)
        except Exception as e:
            self.goruntu_alani.clear_widgets()
            self.goruntu_alani.add_widget(Label(text=f'Acilamadi:\n{str(e)}'))

    def sayfa_hazirla(self, sayfa_no):
        if not self.pdf_renderer: return
        self.islem_yapiyor = True
        self.btn_onceki.disabled = True
        self.btn_sonraki.disabled = True
        
        self.goruntu_alani.clear_widgets()
        self.goruntu_alani.add_widget(Label(text="Sayfa Çiziliyor...\nLütfen Dokunmayın!"))
        
        # Sayfa geçişlerinde de dokunmatik temizliği için 0.4s bekliyoruz
        Clock.schedule_once(lambda dt: self._render_ve_bas(sayfa_no), 0.4)

    def _render_ve_bas(self, sayfa_no):
        try:
            buf = self.pdf_renderer.sayfa_render(sayfa_no, zoom=2.0)
            core_img = CoreImage(buf, ext='png')
            
            self.goruntu_alani.clear_widgets()
            scatter = Scatter(do_rotation=False, scale_min=1.0, scale_max=5.0)
            img = Image(texture=core_img.texture, allow_stretch=True, keep_ratio=True)
            
            img.size = self.goruntu_alani.size
            scatter.size = self.goruntu_alani.size
            
            scatter.add_widget(img)
            self.goruntu_alani.add_widget(scatter)
            
            toplam = self.pdf_renderer.sayfa_sayisi
            self.lbl_sayfa.text = f"{sayfa_no + 1} / {toplam}"
            
            self.islem_yapiyor = False
            self.btn_onceki.disabled = (sayfa_no == 0)
            self.btn_sonraki.disabled = (sayfa_no == toplam - 1)
            
        except Exception as e:
            self.islem_yapiyor = False
            self.goruntu_alani.clear_widgets()
            self.goruntu_alani.add_widget(Label(text=f'Hata:\n{str(e)}'))

    def onceki_sayfa(self, instance):
        if self.mevcut_sayfa > 0 and not self.islem_yapiyor:
            self.mevcut_sayfa -= 1
            self.sayfa_hazirla(self.mevcut_sayfa)

    def sonraki_sayfa(self, instance):
        if self.pdf_renderer and self.mevcut_sayfa < self.pdf_renderer.sayfa_sayisi - 1 and not self.islem_yapiyor:
            self.mevcut_sayfa += 1
            self.sayfa_hazirla(self.mevcut_sayfa)

    def geri_git(self):
        if self.islem_yapiyor: return 
        if self.pdf_renderer:
            self.pdf_renderer.kapat()
        self.geri_func()

class ListeEkrani(Screen):
    def __init__(self, baslik, ogeler, tikla_func, geri_func=None, pdf_mi=False, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical')
        layout.add_widget(ust_bar(baslik, geri_func))
        scroll = ScrollView()
        ic = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(1))
        ic.bind(minimum_height=ic.setter('height'))
        if not ogeler:
            ic.add_widget(Label(text='Icerik bulunamadi!', size_hint_y=None, height=dp(60)))
        for oge in ogeler:
            ad = oge[:-4] if pdf_mi and oge.lower().endswith('.pdf') else oge
            btn = liste_btn(ad, lambda o=oge: tikla_func(o))
            ic.add_widget(btn)
        scroll.add_widget(ic)
        layout.add_widget(scroll)
        self.add_widget(layout)

class DerslerApp(App):
    def build(self):
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])
        except: pass
        try:
            from jnius import autoclass
            Environment = autoclass('android.os.Environment')
            if not Environment.isExternalStorageManager():
                Intent = autoclass('android.content.Intent')
                Settings = autoclass('android.provider.Settings')
                Uri = autoclass('android.net.Uri')
                ctx = autoclass('org.kivy.android.PythonActivity').mActivity
                intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                intent.setData(Uri.parse('package:' + ctx.getPackageName()))
                ctx.startActivity(intent)
        except: pass
        self.sm = ScreenManager()
        self.secili = {}
        self.sinif_ekrani()
        return self.sm

    def temizle(self):
        for s in list(self.sm.screens): self.sm.remove_widget(s)

    def sinif_ekrani(self):
        self.temizle()
        self.sm.add_widget(ListeEkrani(baslik='AOF Derslerim', ogeler=get_dirs(DERSLER_PATH), tikla_func=self.donem_ekrani, name='sinif'))
        self.sm.current = 'sinif'

    def donem_ekrani(self, sinif):
        self.secili['sinif'] = sinif
        self.temizle()
        yol = os.path.join(DERSLER_PATH, sinif)
        self.sm.add_widget(ListeEkrani(baslik=sinif, ogeler=get_dirs(yol), tikla_func=self.ders_ekrani, geri_func=self.sinif_ekrani, name='donem'))
        self.sm.current = 'donem'

    def ders_ekrani(self, donem):
        self.secili['donem'] = donem
        self.temizle()
        yol = os.path.join(DERSLER_PATH, self.secili['sinif'], donem)
        self.sm.add_widget(ListeEkrani(baslik=donem, ogeler=get_dirs(yol), tikla_func=self.pdf_liste, geri_func=lambda: self.donem_ekrani(self.secili['sinif']), name='ders'))
        self.sm.current = 'ders'

    def pdf_liste(self, ders):
        self.secili['ders'] = ders
        self.temizle()
        yol = os.path.join(DERSLER_PATH, self.secili['sinif'], self.secili['donem'], ders)
        self.sm.add_widget(ListeEkrani(baslik=ders, ogeler=get_pdfs(yol), tikla_func=lambda pdf: self.pdf_ac(os.path.join(yol, pdf)), geri_func=lambda: self.ders_ekrani(self.secili['donem']), pdf_mi=True, name='pdfler'))
        self.sm.current = 'pdfler'

    def pdf_ac(self, yol):
        self.temizle()
        self.sm.add_widget(PDFEkrani(pdf_yol=yol, geri_func=lambda: self.pdf_liste(self.secili['ders']), name='pdf'))
        self.sm.current = 'pdf'

DerslerApp().run()
