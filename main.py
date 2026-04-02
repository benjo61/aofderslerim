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

class PDFEkrani(Screen):
    def __init__(self, pdf_yol, geri_func, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical')
        baslik = os.path.basename(pdf_yol)[:-4]
        layout.add_widget(ust_bar(baslik, geri_func))
        scroll = ScrollView()
        sayfa_layout = BoxLayout(orientation='vertical',
            size_hint_y=None, spacing=dp(4), padding=[dp(4), dp(4)])
        sayfa_layout.bind(minimum_height=sayfa_layout.setter('height'))

        try:
            from jnius import autoclass
            PdfRenderer = autoclass('android.graphics.pdf.PdfRenderer')
            ParcelFileDescriptor = autoclass('android.os.ParcelFileDescriptor')
            File = autoclass('java.io.File')
            Bitmap = autoclass('android.graphics.Bitmap')
            BitmapConfig = autoclass('android.graphics.Bitmap$Config')
            ByteArrayOutputStream = autoclass('java.io.ByteArrayOutputStream')
            CompressFormat = autoclass('android.graphics.Bitmap$CompressFormat')

            f = File(pdf_yol)
            pfd = ParcelFileDescriptor.open(f, ParcelFileDescriptor.MODE_READ_ONLY)
            renderer = PdfRenderer(pfd)
            sayfa_sayisi = renderer.getPageCount()

            for i in range(sayfa_sayisi):
                sayfa = renderer.openPage(i)
                w = sayfa.getWidth() * 2
                h = sayfa.getHeight() * 2
                bitmap = Bitmap.createBitmap(w, h, BitmapConfig.ARGB_8888)
                sayfa.render(bitmap, None, None, 1)  # 1 = RENDER_MODE_FOR_DISPLAY
                sayfa.close()

                out = ByteArrayOutputStream()
                bitmap.compress(CompressFormat.PNG, 100, out)
                byte_array = out.toByteArray()
                buf = io.BytesIO(bytes(byte_array))
                core_img = CoreImage(buf, ext='png')
                img = Image(texture=core_img.texture,
                    size_hint_y=None, height=h / 2)
                sayfa_layout.add_widget(img)

            renderer.close()
            pfd.close()

        except Exception as e:
            sayfa_layout.add_widget(Label(
                text=f'PDF acilamadi:\n{str(e)}',
                size_hint_y=None, height=dp(200)))

        scroll.add_widget(sayfa_layout)
        layout.add_widget(scroll)
        self.add_widget(layout)

class DerslerApp(App):
    def build(self):
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
            ])
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
