import os
from kivy.app import App
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

DERSLER_PATH = '/storage/emulated/0/DERSLERİM'

def get_dirs(yol):
    try:
        return sorted([f for f in os.listdir(yol)
            if os.path.isdir(os.path.join(yol, f))])
    except:
        return []

def get_pdfs(yol):
    try:
        return sorted([f for f in os.listdir(yol)
            if f.lower().endswith('.pdf')])
    except:
        return []

class DerslerApp(App):
    def build(self):
        # SINIF sekmeler
        tp = TabbedPanel(do_default_tab=False)
        siniflar = get_dirs(DERSLER_PATH)

        if not siniflar:
            return Label(text='DERSLERİM klasörü boş veya okunamadı!')

        for sinif in siniflar:
            sinif_tab = TabbedPanelItem(text=sinif)
            sinif_yolu = os.path.join(DERSLER_PATH, sinif)

            # DÖNEM sekmeler
            donem_tp = TabbedPanel(do_default_tab=False)
            donemler = get_dirs(sinif_yolu)

            for donem in donemler:
                donem_tab = TabbedPanelItem(text=donem)
                donem_yolu = os.path.join(sinif_yolu, donem)

                # DERS sekmeler
                ders_tp = TabbedPanel(do_default_tab=False)
                dersler = get_dirs(donem_yolu)

                for ders in dersler:
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
                                size_hint_y=None, height=75,
                                font_size=13, halign='center',
                                text_size=(None, None))
                            pdf_yol = os.path.join(ders_yolu, pdf)
                            btn.bind(on_press=lambda x, p=pdf_yol: self.pdf_ac(p))
                            layout.add_widget(btn)

                    scroll.add_widget(layout)
                    ders_tab.add_widget(scroll)
                    ders_tp.add_widget(ders_tab)

                donem_tab.add_widget(ders_tp)
                donem_tp.add_widget(donem_tab)

            sinif_tab.add_widget(donem_tp)
            tp.add_widget(sinif_tab)

        return tp

    def pdf_ac(self, yol):
        try:
            from jnius import autoclass
            from android import activity
            Intent = autoclass('android.content.Intent')
            Uri = autoclass('android.net.Uri')
            FileProvider = autoclass('androidx.core.content.FileProvider')
            File = autoclass('java.io.File')
            context = autoclass('org.kivy.android.PythonActivity').mActivity
            dosya = File(yol)
            uri = FileProvider.getUriForFile(context,
                context.getPackageName() + '.fileprovider', dosya)
            intent = Intent(Intent.ACTION_VIEW)
            intent.setDataAndType(uri, 'application/pdf')
            intent.setFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            context.startActivity(intent)
        except Exception as e:
            print(f'Hata: {e}')

DerslerApp().run()
