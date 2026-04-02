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
    bar.canvas.before.clear()
    from kivy.graphics import Color, Rectangle
    with bar.canvas.before:
        Color(0.2, 0.5, 0.8, 1)
        bar.rect = Rectangle(pos=bar.pos, size=bar.size)
    bar.bind(pos=lambda *a: setattr(bar.rect, 'pos', bar.pos))
    bar.bind(size=lambda *a: setattr(bar.rect, 'size', bar.size))
    if geri_func:
        geri = Button(text='←', size_hint_x=None, width=dp(50),
            background_color=(0.1, 0.4, 0.7, 1), font_size=dp(22))
        geri.bind(on_press=lambda x: geri_func())
        bar.add_widget(geri)
    lbl = Label(text=baslik, font_size=dp(18), bold=True, halign='left',
        text_size=(None, None))
    bar.add_widget(lbl)
    return bar

def liste_btn(metin, callback):
    btn = Button(
        text=metin,
        size_hint_y=None,
        height=dp(65),
        font_size=dp(15),
        halign='left',
        padding_x=dp(15),
        background_color=(0.15, 0.15, 0.15, 1),
        background_normal=''
    )
    btn.bind(on_press=lambda x: callback())
    return btn

def ayrac():
    from kivy.uix.widget import Widget
    from kivy.graphics import Color, Rectangle
    w = Widget(size_hint_y=None, height=dp(1))
    with w.canvas:
        Color(0.3, 0.3, 0.3, 1)
        Rectangle(pos=w.pos, size=w.size)
    w.bind(pos=lambda *a: w.canvas.clear() or
        w.canvas.__class__.clear(w.canvas) or None)
    return w

class ListeEkrani(Screen):
    def __init__(self, baslik, ogeler, tikla_func, geri_func=None, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical')
        layout.add_widget(ust_bar(baslik, geri_func))
        scroll = ScrollView()
        ic = BoxLayout(orientation='vertical',
            size_hint_y=None, spacing=dp(1), padding=[0, dp(5)])
        ic.bind(minimum_height=ic.setter('height'))
        if not ogeler:
            ic.add_widget(Label(text='Klasör boş!',
                size_hint_y=None, height=dp(60)))
        for oge in ogeler:
            btn = liste_btn('   📁  ' + oge if not oge.endswith('.pdf')
                else '   📄  ' + oge[:-4], lambda o=oge: tikla_func(o))
            ic.add_widget(btn)
            ic.add_widget(ayrac())
        scroll.add_widget(ic)
        layout.add_widget(scroll)
        self.add_widget(layout)

class PDFEkrani(Screen):
    def __init__(self, pdf_yol, geri_func, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical')
        layout.add_widget(ust_bar(os.path.basename(pdf_yol)[:-4], geri_func))
        scroll = ScrollView()
        sayfa_layout = BoxLayout(orientation='vertical',
            size_hint_y=None, spacing=dp(5), padding=[dp(5), dp(5)])
        sayfa_layout.bind(minimum_height=sayfa_layout.setter('height'))
        try:
            import fitz
            doc = fitz.open(pdf_yol)
            for i in range(len(doc)):
                pix = doc[i].get_pixmap(matrix=fitz.Matrix(2, 2))
                buf = io.BytesIO(pix.tobytes('png'))
                core_img = CoreImage(buf, ext='png')
                img = Image(texture=core_img.texture,
                    size_hint_y=None, height=pix.height / 2)
                sayfa_layout.add_widget(img)
            doc.close()
        except Exception as e:
            sayfa_layout.add_widget(Label(
                text=f'PDF açılamadı:\n{str(e)}',
                size_hint_y=None, height=dp(150)))
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
                context = autoclass('org.kivy.android.PythonActivity').mActivity
                intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                intent.setData(Uri.parse('package:' + context.getPackageName()))
                context.startActivity(intent)
        except:
            pass
        self.sm = ScreenManager()
        self.gecmis = []
        self.sinif_ekrani()
        return self.sm

    def ekran_temizle(self):
        for s in list(self.sm.screens):
            self.sm.remove_widget(s)

    def sinif_ekrani(self):
        self.ekran_temizle()
        siniflar = get_dirs(DERSLER_PATH)
        ekran = ListeEkrani(
            baslik='AÖF Derslerim',
            ogeler=siniflar,
            tikla_func=self.donem_ekrani,
            name='sinif'
        )
        self.sm.add_widget(ekran)
        self.sm.current = 'sinif'

    def donem_ekrani(self, sinif):
        self.secili_sinif = sinif
        self.ekran_temizle()
        yol = os.path.join(DERSLER_PATH, sinif)
        ekran = ListeEkrani(
            baslik=sinif,
            ogeler=get_dirs(yol),
            tikla_func=self.ders_ekrani,
            geri_func=self.sinif_ekrani,
            name='donem'
        )
        self.sm.add_widget(ekran)
        self.sm.current = 'donem'

    def ders_ekrani(self, donem):
        self.secili_donem = donem
        self.ekran_temizle()
        yol = os.path.join(DERSLER_PATH, self.secili_sinif, donem)
        ekran = ListeEkrani(
            baslik=donem,
            ogeler=get_dirs(yol),
            tikla_func=self.pdf_liste_ekrani,
            geri_func=lambda: self.donem_ekrani(self.secili_sinif),
            name='ders'
        )
        self.sm.add_widget(ekran)
        self.sm.current = 'ders'

    def pdf_liste_ekrani(self, ders):
        self.secili_ders = ders
        self.ekran_temizle()
        yol = os.path.join(DERSLER_PATH, self.secili_sinif, self.secili_donem, ders)
        pdfler = get_pdfs(yol)
        ekran = ListeEkrani(
            baslik=ders,
            ogeler=pdfler,
            tikla_func=lambda pdf: self.pdf_ac(os.path.join(yol, pdf)),
            geri_func=lambda: self.ders_ekrani(self.secili_donem),
            name='pdfler'
        )
        self.sm.add_widget(ekran)
        self.sm.current = 'pdfler'

    def pdf_ac(self, yol):
        self.ekran_temizle()
        ekran = PDFEkrani(
            pdf_yol=yol,
            geri_func=lambda: self.pdf_liste_ekrani(self.secili_ders),
            name='pdf'
        )
        self.sm.add_widget(ekran)
        self.sm.current = 'pdf'

DerslerApp().run()
