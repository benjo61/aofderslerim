import os, io, threading
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
from kivy.core.window import Window

DERSLER_PATH = '/storage/emulated/0/DERSLERİM'

def get_dirs(yol):
    try:
        return sorted([f for f in os.listdir(yol) if os.path.isdir(os.path.join(yol, f))])
    except:
        return []

def get_pdfs(yol):
    try:
        return sorted([f for f in os.listdir(yol) if f.lower().endswith('.pdf')])
    except:
        return []

def ust_bar(baslik, geri_func=None):
    bar = BoxLayout(size_hint_y=None, height=dp(56),
        padding=[dp(10), dp(8)], spacing=dp(10))
    with bar.canvas.before:
        Color(0.2, 0.5, 0.8, 1)
        rect = Rectangle(pos=bar.pos, size=bar.size)
    bar.bind(pos=lambda *a: setattr(rect, 'pos', bar.pos))
    bar.bind(size=lambda *a: setattr(rect, 'size', bar.size))
    if geri_func:
        geri = Button(text='< Geri', size_hint_x=None, width=dp(90),
            background_color=(0.1, 0.4, 0.7, 1), font_size=dp(16))
        geri.bind(on_press=lambda x: geri_func())
        bar.add_widget(geri)
    bar.add_widget(Label(text=baslik, font_size=dp(17), bold=True))
    return bar

def liste_btn(metin, callback):
    btn = Button(text=metin, size_hint_y=None, height=dp(65),
        font_size=dp(15), halign='left', padding_x=dp(15),
        background_color=(0.15, 0.15, 0.15, 1), background_normal='')
    btn.bind(on_press=lambda x: callback())
    return btn

class PDFRenderer:
    def __init__(self, pdf_yol):
        from jnius import autoclass
        PdfRenderer = autoclass('android.graphics.pdf.PdfRenderer')
        ParcelFileDescriptor = autoclass('android.os.ParcelFileDescriptor')
        File = autoclass('java.io.File')
        f = File(pdf_yol)
        self.pfd = ParcelFileDescriptor.open(f, ParcelFileDescriptor.MODE_READ_ONLY)
        self.renderer = PdfRenderer(self.pfd)
        self.sayfa_sayisi = self.renderer.getPageCount()
        self.kilit = threading.Lock()  # MUTEX

    def sayfa_render(self, sayfa_no):
        from jnius import autoclass
        Bitmap = autoclass('android.graphics.Bitmap')
        BitmapConfig = autoclass('android.graphics.Bitmap$Config')
        Canvas = autoclass('android.graphics.Canvas')
        PaintColor = autoclass('android.graphics.Color')
        ByteArrayOutputStream = autoclass('java.io.ByteArrayOutputStream')
        CompressFormat = autoclass('android.graphics.Bitmap$CompressFormat')

        with self.kilit:  # Aynı anda sadece 1 sayfa
            sayfa = self.renderer.openPage(sayfa_no)
            w = sayfa.getWidth() * 2
            h = sayfa.getHeight() * 2
            bitmap = Bitmap.createBitmap(w, h, BitmapConfig.ARGB_8888)
            canvas = Canvas(bitmap)
            canvas.drawColor(PaintColor.WHITE)
            sayfa.render(bitmap, None, None, 1)
            sayfa.close()
            out = ByteArrayOutputStream()
            bitmap.compress(CompressFormat.PNG, 90, out)
            buf = io.BytesIO(bytes(out.toByteArray()))
            return buf, w, h

    def kapat(self):
        try:
            self.renderer.close()
            self.pfd.close()
        except:
            pass

class SayfaWidget(BoxLayout):
    def __init__(self, sayfa_no, pdf_renderer, zoom_ref, **kwargs):
        super().__init__(**kwargs)
        self.sayfa_no = sayfa_no
        self.pdf_renderer = pdf_renderer
        self.zoom_ref = zoom_ref
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = dp(500)
        self.yuklendi = False
        self.yukleniyor = False
        self.img_widget = None
        self.base_h = dp(500)
        self.add_widget(Label(
            text=f'Sayfa {sayfa_no + 1}',
            size_hint_y=None, height=dp(500),
            color=(0.5, 0.5, 0.5, 1)))

    def yukle(self):
        if self.yuklendi or self.yukleniyor:
            return
        self.yukleniyor = True
        t = threading.Thread(target=self._yukle_thread)
        t.daemon = True
        t.start()

    def _yukle_thread(self):
        try:
            buf, w, h = self.pdf_renderer.sayfa_render(self.sayfa_no)
            Clock.schedule_once(lambda dt: self._goster(buf, w, h), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self._hata(str(e)), 0)

    def _goster(self, buf, w, h):
        zoom = self.zoom_ref[0]
        self.base_h = Window.width * (h / w)
        goster_h = self.base_h * zoom
        core_img = CoreImage(buf, ext='png')
        img = Image(texture=core_img.texture,
            size_hint_y=None, height=goster_h,
            allow_stretch=True, keep_ratio=True)
        self.img_widget = img
        self.clear_widgets()
        self.height = goster_h
        self.add_widget(img)
        self.yuklendi = True

    def _hata(self, msg):
        self.clear_widgets()
        self.add_widget(Label(text=f'Hata: {msg}',
            size_hint_y=None, height=dp(80)))

    def zoom_guncelle(self, zoom):
        if self.img_widget:
            yeni_h = self.base_h * zoom
            self.img_widget.height = yeni_h
            self.height = yeni_h

class LazyPDFScroll(ScrollView):
    def __init__(self, pdf_renderer, **kwargs):
        super().__init__(**kwargs)
        self.pdf_renderer = pdf_renderer
        self.zoom_ref = [1.0]
        self.sayfalar = []
        self.ic = BoxLayout(orientation='vertical',
            size_hint_y=None, spacing=dp(6),
            padding=[dp(4), dp(4)])
        self.ic.bind(minimum_height=self.ic.setter('height'))
        for i in range(pdf_renderer.sayfa_sayisi):
            sw = SayfaWidget(sayfa_no=i, pdf_renderer=pdf_renderer,
                zoom_ref=self.zoom_ref)
            self.sayfalar.append(sw)
            self.ic.add_widget(sw)
        self.add_widget(self.ic)
        self.bind(scroll_y=self.scroll_degisti)
        Clock.schedule_once(lambda dt: self.ilk_yukle(), 0.3)

    def ilk_yukle(self):
        for i in range(min(3, len(self.sayfalar))):
            self.sayfalar[i].yukle()

    def scroll_degisti(self, *args):
        Clock.schedule_once(lambda dt: self.gorunen_yukle(), 0.2)

    def gorunen_yukle(self):
        if not self.sayfalar:
            return
        toplam = len(self.sayfalar)
        oran = 1 - self.scroll_y
        orta = int(oran * toplam)
        for i in range(max(0, orta - 1), min(toplam, orta + 4)):
            self.sayfalar[i].yukle()

    def zoom_yap(self, delta):
        self.zoom_ref[0] = max(0.5, min(3.0, self.zoom_ref[0] + delta))
        for s in self.sayfalar:
            s.zoom_guncelle(self.zoom_ref[0])

class PDFEkrani(Screen):
    def __init__(self, pdf_yol, geri_func, **kwargs):
        super().__init__(**kwargs)
        self.geri_func = geri_func
        self.pdf_renderer = None
        layout = BoxLayout(orientation='vertical')
        baslik = os.path.basename(pdf_yol)[:-4]
        layout.add_widget(ust_bar(baslik, self.geri_git))
        try:
            self.pdf_renderer = PDFRenderer(pdf_yol)
            self.lazy_scroll = LazyPDFScroll(pdf_renderer=self.pdf_renderer)
            zoom_bar = BoxLayout(size_hint_y=None, height=dp(55),
                spacing=dp(5), padding=[dp(5), dp(8)])
            with zoom_bar.canvas.before:
                Color(0.1, 0.1, 0.1, 1)
                r2 = Rectangle(pos=zoom_bar.pos, size=zoom_bar.size)
            zoom_bar.bind(pos=lambda *a: setattr(r2, 'pos', zoom_bar.pos))
            zoom_bar.bind(size=lambda *a: setattr(r2, 'size', zoom_bar.size))
            btn_k = Button(text='−', font_size=dp(26),
                background_color=(0.2, 0.5, 0.8, 1), background_normal='')
            btn_b = Button(text='+', font_size=dp(26),
                background_color=(0.2, 0.5, 0.8, 1), background_normal='')
            self.zoom_lbl = Label(text='%100', font_size=dp(16), size_hint_x=0.5)
            btn_k.bind(on_press=lambda x: self.zoom(-0.15))
            btn_b.bind(on_press=lambda x: self.zoom(0.15))
            zoom_bar.add_widget(btn_k)
            zoom_bar.add_widget(self.zoom_lbl)
            zoom_bar.add_widget(btn_b)
            layout.add_widget(self.lazy_scroll)
            layout.add_widget(zoom_bar)
        except Exception as e:
            layout.add_widget(Label(text=f'PDF acilamadi:\n{str(e)}'))
        self.add_widget(layout)

    def zoom(self, delta):
        self.lazy_scroll.zoom_yap(delta)
        yuzde = int(self.lazy_scroll.zoom_ref[0] * 100)
        self.zoom_lbl.text = f'%{yuzde}'

    def geri_git(self):
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
            ic.add_widget(Label(text='Icerik bulunamadi!',
                size_hint_y=None, height=dp(60)))
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
            request_permissions([Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE])
        except:
            pass
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
        except:
            pass
        self.sm = ScreenManager()
        self.secili = {}
        self.sinif_ekrani()
        return self.sm

    def temizle(self):
        for s in list(self.sm.screens):
            self.sm.remove_widget(s)

    def sinif_ekrani(self):
        self.temizle()
        e = ListeEkrani(baslik='AOF Derslerim',
            ogeler=get_dirs(DERSLER_PATH),
            tikla_func=self.donem_ekrani, name='sinif')
        self.sm.add_widget(e)
        self.sm.current = 'sinif'

    def donem_ekrani(self, sinif):
        self.secili['sinif'] = sinif
        self.temizle()
        yol = os.path.join(DERSLER_PATH, sinif)
        e = ListeEkrani(baslik=sinif, ogeler=get_dirs(yol),
            tikla_func=self.ders_ekrani,
            geri_func=self.sinif_ekrani, name='donem')
        self.sm.add_widget(e)
        self.sm.current = 'donem'

    def ders_ekrani(self, donem):
        self.secili['donem'] = donem
        self.temizle()
        yol = os.path.join(DERSLER_PATH, self.secili['sinif'], donem)
        e = ListeEkrani(baslik=donem, ogeler=get_dirs(yol),
            tikla_func=self.pdf_liste,
            geri_func=lambda: self.donem_ekrani(self.secili['sinif']),
            name='ders')
        self.sm.add_widget(e)
        self.sm.current = 'ders'

    def pdf_liste(self, ders):
        self.secili['ders'] = ders
        self.temizle()
        yol = os.path.join(DERSLER_PATH, self.secili['sinif'],
            self.secili['donem'], ders)
        e = ListeEkrani(baslik=ders, ogeler=get_pdfs(yol),
            tikla_func=lambda pdf: self.pdf_ac(os.path.join(yol, pdf)),
            geri_func=lambda: self.ders_ekrani(self.secili['donem']),
            pdf_mi=True, name='pdfler')
        self.sm.add_widget(e)
        self.sm.current = 'pdfler'

    def pdf_ac(self, yol):
        self.temizle()
        e = PDFEkrani(pdf_yol=yol,
            geri_func=lambda: self.pdf_liste(self.secili['ders']),
            name='pdf')
        self.sm.add_widget(e)
        self.sm.current = 'pdf'

DerslerApp().run()
