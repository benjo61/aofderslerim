import os, io
from kivy.app import App
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.image import Image as CoreImage

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

class PDFScreen(Screen):
    def __init__(self, pdf_yol, geri_func, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical')

        ust = BoxLayout(size_hint_y=None, height=60, padding=[5,5], spacing=5)
        geri_btn = Button(text='← Geri', size_hint_x=None, width=120)
        geri_btn.bind(on_press=lambda x: geri_func())
        baslik = Label(text=os.path.basename(pdf_yol)[:-4], font_size=13)
        ust.add_widget(geri_btn)
        ust.add_widget(baslik)
        layout.add_widget(ust)

        scroll = ScrollView()
        sayfa_layout = BoxLayout(orientation='vertical',
            size_hint_y=None, spacing=5, padding=[5,5])
        sayfa_layout.bind(minimum_height=sayfa_layout.setter('height'))

        try:
            import fitz
            doc = fitz.open(pdf_yol)
            for i in range(len(doc)):
                sayfa = doc[i]
                pix = sayfa.get_pixmap(matrix=fitz.Matrix(2, 2))
                buf = io.BytesIO(pix.tobytes('png'))
                core_img = CoreImage(buf, ext='png')
                img = Image(texture=core_img.texture,
                    size_hint_y=None, height=pix.height / 2)
                sayfa_layout.add_widget(img)
            doc.close()
        except Exception as e:
            sayfa_layout.add_widget(Label(
                text=f'PDF açılamadı:\n{str(e)}',
                size_hint_y=None, height=200))

        scroll.add_widget(sayfa_layout)
        layout.add_widget(scroll)
        self.add_widget(layout)

class AnaSayfa(Screen):
    def __init__(self, pdf_ac_func, **kwargs):
        super().__init__(**kwargs)
        tp = TabbedPanel(do_default_tab=False)
        siniflar = get_dirs(DERSLER_PATH)

        if not siniflar:
            self.add_widget(Label(text='DERSLERİM klasörü boş!'))
            return

        for sinif in siniflar:
            sinif_tab = TabbedPanelItem(text=sinif)
            sinif_yolu = os.path.join(DERSLER_PATH, sinif)
            donem_tp = TabbedPanel(do_default_tab=False)

            for donem in get_dirs(sinif_yolu):
                donem_tab = TabbedPanelItem(text=donem)
                donem_yolu = os.path.join(sinif_yolu, donem)
                ders_tp = TabbedPanel(do_default_tab=False)

                for ders in get_dirs(donem_yolu):
                    ders_tab = TabbedPanelItem(text=ders)
                    ders_yolu = os.path.join(donem_yolu, ders)
                    scroll = ScrollView()
                    layout = BoxLayout(orientation='vertical',
                        size_hint_y=None, padding=[10,10], spacing=8)
                    layout.bind(minimum_height=layout.setter('height'))

                    pdfler = get_pdfs(ders_yolu)
                    if not pdfler:
                        layout.add_widget(Label(
                            text='PDF bulunamadı.',
                            size_hint_y=None, height=60))
                    else:
                        for pdf in pdfler:
                            btn = Button(text=pdf[:-4],
                                size_hint_y=None, height=75, font_size=13)
                            pdf_yol = os.path.join(ders_yolu, pdf)
                            btn.bind(on_press=lambda x, p=pdf_yol: pdf_ac_func(p))
                            layout.add_widget(btn)

                    scroll.add_widget(layout)
                    ders_tab.add_widget(scroll)
                    ders_tp.add_widget(ders_tab)

                donem_tab.add_widget(ders_tp)
                donem_tp.add_widget(donem_tab)

            sinif_tab.add_widget(donem_tp)
            tp.add_widget(sinif_tab)

        self.add_widget(tp)

class DerslerApp(App):
    def build(self):
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
            ], lambda *x: None)
        except:
            pass

        self.sm = ScreenManager()
        ana = AnaSayfa(pdf_ac_func=self.pdf_ac, name='ana')
        self.sm.add_widget(ana)
        return self.sm

    def pdf_ac(self, yol):
        if self.sm.has_screen('pdf'):
            self.sm.remove_widget(self.sm.get_screen('pdf'))
        pdf_screen = PDFScreen(pdf_yol=yol, geri_func=self.geri_don, name='pdf')
        self.sm.add_widget(pdf_screen)
        self.sm.current = 'pdf'

    def geri_don(self):
        self.sm.current = 'ana'

DerslerApp().run()
