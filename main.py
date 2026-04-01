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
            klasorler = sorted([
                f for f in os.listdir(DERSLER_PATH)
                if os.path.isdir(os.path.join(DERSLER_PATH, f))
            ])
        except Exception as e:
            return Label(text=f'Klasör okunamadı:\n{str(e)}', halign='center')

        if not klasorler:
            return Label(text='DERSLERİM klasörü boş!', halign='center')

        for klasor in klasorler:
            tab = TabbedPanelItem(text=klasor)
            klasor_yolu = os.path.join(DERSLER_PATH, klasor)

            scroll = ScrollView()
            layout = BoxLayout(
                orientation='vertical',
                size_hint_y=None,
                padding=[10, 10],
                spacing=8
            )
            layout.bind(minimum_height=layout.setter('height'))

            try:
                pdfler = sorted([
                    f for f in os.listdir(klasor_yolu)
                    if f.lower().endswith('.pdf')
                ])
            except:
                pdfler = []

            if not pdfler:
                layout.add_widget(Label(
                    text='Bu klasörde PDF bulunamadı.',
                    size_hint_y=None,
                    height=60
                ))
            else:
                for pdf in pdfler:
                    btn = Button(
                        text=pdf[:-4] if pdf.lower().endswith('.pdf') else pdf,
                        size_hint_y=None,
                        height=75,
                        font_size=15,
                        halign='center',
                        text_size=(None, None)
                    )
                    pdf_tam_yol = os.path.join(klasor_yolu, pdf)
                    btn.bind(on_press=lambda x, p=pdf_tam_yol: self.pdf_ac(p))
                    layout.add_widget(btn)

            scroll.add_widget(layout)
            tab.add_widget(scroll)
            tp.add_widget(tab)

        return tp

    def pdf_ac(self, yol):
        try:
            from jnius import autoclass
            from android import activity
            Intent = autoclass('android.content.Intent')
            Uri = autoclass('android.net.Uri')
            File = autoclass('java.io.File')
            dosya = File(yol)
            uri = Uri.fromFile(dosya)
            intent = Intent(Intent.ACTION_VIEW)
            intent.setDataAndType(uri, 'application/pdf')
            intent.setFlags(Intent.FLAG_ACTIVITY_NO_HISTORY)
            activity.startActivity(intent)
        except Exception as e:
            print(f'PDF açma hatası: {e}')

DerslerApp().run()
