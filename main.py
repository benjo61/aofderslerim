import os
from kivy.app import App
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

DERSLER_PATH = '/storage/emulated/0/DERSLERİM'

class DerslerApp(App):
    def build(self):
        tp = TabbedPanel(do_default_tab=False)
        try:
            siniflar = sorted([f for f in os.listdir(DERSLER_PATH)
                if os.path.isdir(os.path.join(DERSLER_PATH, f))])
        except Exception as e:
            return Label(text=f'Hata: {str(e)}')

        for sinif in siniflar:
            sinif_tab = TabbedPanelItem(text=sinif)
            sinif_yolu = os.path.join(DERSLER_PATH, sinif)

            ic_tp = TabbedPanel(do_default_tab=False)

            try:
                donemler = sorted([f for f in os.listdir(sinif_yolu)
                    if os.path.isdir(os.path.join(sinif_yolu, f))])
            except:
                donemler = []

            for donem in donemler:
                donem_tab = TabbedPanelItem(text=donem)
                donem_yolu = os.path.join(sinif_yolu, donem)

                scroll = ScrollView()
                layout = BoxLayout(orientation='vertical',
                    size_hint_y=None, padding=[10,10], spacing=8)
                layout.bind(minimum_height=layout.setter('height'))

                try:
                    pdfler = sorted([f for f in os.listdir(donem_yolu)
                        if f.lower().endswith('.pdf')])
                except:
                    pdfler = []

                if not pdfler:
                    layout.add_widget(Label(
                        text='PDF bulunamadı.',
                        size_hint_y=None, height=60))
                else:
                    for pdf in pdfler:
                        btn = Button(text=pdf[:-4],
                            size_hint_y=None, height=75, font_size=15)
                        pdf_yol = os.path.join(donem_yolu, pdf)
                        btn.bind(on_press=lambda x, p=pdf_yol: self.pdf_ac(p))
                        layout.add_widget(btn)

                scroll.add_widget(layout)
                donem_tab.add_widget(scroll)
                ic_tp.add_widget(donem_tab)

            sinif_tab.add_widget(ic_tp)
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
