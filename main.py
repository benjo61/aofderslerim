import os
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from kivy.uix.scatter import Scatter
from kivy.cache import Cache

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
        geri.bind(on_release=lambda x: geri_func())
        bar.add_widget(geri)
    bar.add_widget(Label(text=baslik, font_size=dp(17), bold=True))
    return bar

def liste_btn(metin, callback):
    btn = Button(text=metin, size_hint_y=None, height=dp(65), font_size=dp(15), halign='left', padding_x=dp(15), background_color=(0.15, 0.15, 0.15, 1), background_normal='')
    btn.bind(on_release=lambda x: callback())
    return btn

# --- JNI KÖPRÜSÜNÜ BAYPAS EDEN DİSK MOTORU ---
class PDFRenderer:
    def __init__(self, pdf_yol):
        from jnius import autoclass
        self.PdfRenderer = autoclass('android.graphics.pdf.PdfRenderer')
        self.ParcelFileDescriptor = autoclass('android.os.ParcelFileDescriptor')
        self.File = autoclass('java.io.File')
        
        f = self.File(pdf_yol)
        self.pfd = self.ParcelFileDescriptor.open(f, self.ParcelFileDescriptor.MODE_READ_ONLY)
        self.renderer = self.PdfRenderer(self.pfd)
        self.sayfa_sayisi = self.renderer.getPageCount()

    def sayfa_render(self, sayfa_no, zoom=1.5):
        from jnius import autoclass
        Bitmap = autoclass('android.graphics.Bitmap')
        BitmapConfig = autoclass('android.graphics.Bitmap$Config')
        CompressFormat = autoclass('android.graphics.Bitmap$CompressFormat')
        FileOutputStream = autoclass('java.io.FileOutputStream')
        File = autoclass('java.io.File')

        bitmap = None
        fos = None
        temp_path = os.path.join(DERSLER_PATH, '.cache_page.png')
        
        try:
            sayfa = self.renderer.openPage(sayfa_no)
            w = int(sayfa.getWidth() * zoom)
            h = int(sayfa.getHeight() * zoom)
            
            # Resmi oluştur ve arka planı (-1 = Beyaz) renge boya (Canvas iptal, daha güvenli)
            bitmap = Bitmap.createBitmap(w, h, BitmapConfig.ARGB_8888)
            bitmap.eraseColor(-1)
            sayfa.render(bitmap, None, None, 1)
            sayfa.close()
            
            # Devasa veriyi JNI'dan geçirmek yerine doğrudan diske ışınlıyoruz!
            cache_file = File(temp_path)
            fos = FileOutputStream(cache_file)
            bitmap.compress(CompressFormat.PNG, 90, fos)
            
            return temp_path
        finally:
            if bitmap:
                try: bitmap.recycle()
                except: pass
            if fos:
                try: fos.close()
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
        
        self.goruntu_alani = BoxLayout(orientation='vertical')
        self.layout.add_widget(self.goruntu_alani)
        
        alt_bar = BoxLayout(size_hint_y=None, height=dp(60), padding=dp(5), spacing=dp(10))
        with alt_bar.canvas.before:
            Color(0.1, 0.1, 0.1, 1)
            self.alt_rect = Rectangle(pos=alt_bar.pos, size=alt_bar.size)
        alt_bar.bind(pos=lambda *a: setattr(self.alt_rect, 'pos', alt_bar.pos))
        alt_bar.bind(size=lambda *a: setattr(self.alt_rect, 'size', alt_bar.size))
        
        self.btn_onceki = Button(text='<< ONCEKI', font_size=dp(14), background_color=(0.2, 0.5, 0.8, 1))
        self.btn_onceki.bind(on_release=self.onceki_sayfa)
        
        self.lbl_sayfa = Label(text='Hazirlaniyor...', bold=True)
        
        self.btn_sonraki = Button(text='SONRAKI >>', font_size=dp(14), background_color=(0.2, 0.5, 0.8, 1))
        self.btn_sonraki.bind(on_release=self.sonraki_sayfa)
        
        alt_bar.add_widget(self.btn_onceki)
        alt_bar.add_widget(self.lbl_sayfa)
        alt_bar.add_widget(self.btn_sonraki)
        
        self.layout.add_widget(alt_bar)
        self.add_widget(self.layout)

    def on_enter(self):
        Clock.schedule_once(self.baslat, 0.2)

    def baslat(self, dt):
        try:
            self.pdf_renderer = PDFRenderer(self.pdf_yol)
            self.sayfa_goster(self.mevcut_sayfa)
        except Exception as e:
            self.goruntu_alani.clear_widgets()
            self.goruntu_alani.add_widget(Label(text=f'Motor Acilamadi:\n{str(e)}'))

    def sayfa_goster(self, sayfa_no):
        if not self.pdf_renderer: return
        self.islem_yapiyor = True
        self.btn_onceki.disabled = True
        self.btn_sonraki.disabled = True
        
        self.goruntu_alani.clear_widgets()
        self.goruntu_alani.add_widget(Label(text="Sayfa Çiziliyor..."))
        
        Clock.schedule_once(lambda dt: self._render_ve_bas(sayfa_no), 0.1)

    def _render_ve_bas(self, sayfa_no):
        try:
            # 1. Java arka planda resmi DİSKE yazar. RAM şişmez, JNI çökmez.
            cache_yol = self.pdf_renderer.sayfa_render(sayfa_no, zoom=1.5)
            
            # 2. Kivy'nin hep aynı dosyayı göstermemesi için önbelleğini siliyoruz
            Cache.remove('kv.image')
            Cache.remove('kv.texture')
            
            self.goruntu_alani.clear_widgets()
            scatter = Scatter(do_rotation=False, scale_min=1.0, scale_max=4.0)
            
            # 3. Kivy sadece diskteki dosyayı okur!
            img = Image(source=cache_yol, allow_stretch=True, keep_ratio=True)
            img.reload()
            
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
            self.goruntu_alani.add_widget(Label(text=f'Sayfa Hatası:\n{str(e)}'))

    def onceki_sayfa(self, instance):
        if self.mevcut_sayfa > 0 and not self.islem_yapiyor:
            self.mevcut_sayfa -= 1
            self.sayfa_goster(self.mevcut_sayfa)

    def sonraki_sayfa(self, instance):
        if self.pdf_renderer and self.mevcut_sayfa < self.pdf_renderer.sayfa_sayisi - 1 and not self.islem_yapiyor:
            self.mevcut_sayfa += 1
            self.sayfa_goster(self.mevcut_sayfa)

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
