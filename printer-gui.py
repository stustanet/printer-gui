#!/usr/bin/python
# vim: set fileencoding=utf-8 ts=4 sts=4 et:

PRICE_CMD = '/usr/local/bin/printer_pricecalc.py'
LOGO = '/usr/local/share/ssn/StuStaNet_Logo.svg'
# look also at uploaded.py

import subprocess

import pygtk
pygtk.require('2.0')
import gtk
import gobject

from uploaded import UploadedFile

class PrinterGui:
    # file to print
    file = None

    # duplex and blackwhite settings
    duplex = None
    blackwhite = False

    # current state
    state = None

    # price of printout
    price = 0

    # state for progress
    progress_state = True

    count_proc = None
    price_buffer = ""

    def __init__(self):
        """Create window, callbacks, ..."""
        # create window
        self.win = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.win.set_title("StuStaNet Druckservice")
        self.win.set_border_width(5)
        
        # create central vbox
        self.vbox = gtk.VBox(homogeneous=False, spacing=0)

        # logo
        frm = gtk.Frame()
        logo = gtk.Image()
        logo.set_from_file(LOGO)
        logo.show()
        frm.add(logo)
        frm.show()
        self.vbox.pack_start(frm)

        # ensure proper end of application
        self.win.connect('delete_event', lambda w, e: gtk.main_quit())
        self.win.connect('destroy', self.quit)


        # uploaded files
        frm = gtk.Frame(label=" Hochgeladene Dateien ")
        self.upl_hbox = gtk.HBox(homogeneous=False, spacing=0)
        self.upl_hbox.set_border_width(5)
        lbl = gtk.Label("PIN: ")
        lbl.show()
        self.upl_hbox.pack_start(lbl, fill=False, expand=False)
        self.pin_input = gtk.Entry()
        self.pin_input.show()
        self.upl_hbox.pack_start(self.pin_input)
        self.upl_button = gtk.Button("Laden")
        self.upl_button.connect('clicked', self.load_uploaded, None)
        self.upl_button.show()
        self.upl_hbox.pack_start(self.upl_button, padding=5, fill=False, expand=False)
        self.upl_hbox.show()
        frm.add(self.upl_hbox)
        frm.show()
        self.vbox.pack_start(frm)

        # file chooser button
        frm = gtk.Frame(label=' Dateien von USB-Stick oder Festplatte ')
        hbox = gtk.HBox(homogeneous=False, spacing=0)
        hbox.set_border_width(5)
        self.open_filter = gtk.FileFilter()
        self.open_filter.add_pattern('*.pdf')
        self.open_filter.set_name('PDF Dateien')
        self.chooser_dialog = gtk.FileChooserDialog(
                action=gtk.FILE_CHOOSER_ACTION_OPEN,
                title='Datei drucken',
                buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                    gtk.STOCK_OK, gtk.RESPONSE_ACCEPT)
            )
        self.chooser_dialog.set_local_only(True)
        self.chooser_dialog.set_select_multiple(False)
        self.chooser_dialog.set_filter(self.open_filter)
        self.open_button = gtk.FileChooserButton(self.chooser_dialog)
        self.open_button.set_width_chars(30)
        self.open_button.connect('file-set', self.file_selected, None)
        self.open_button.show()
        lbl = gtk.Label('Datei öffnen: ')
        lbl.show()
        hbox.pack_start(lbl, expand=False, fill=False)
        hbox.pack_start(self.open_button)
        hbox.show()
        frm.add(hbox)
        frm.show()
        self.vbox.pack_start(frm)

        # duplex and b/w checkboxes
        frm = gtk.Frame(" Druckeinstellungen ")
        vbox = gtk.VBox(homogeneous=False, spacing=0)
        self.bw_checkbox = gtk.CheckButton(label="Schwarz / Weiss")
        self.bw_checkbox.show()
        self.simplex_radio = gtk.RadioButton(None, "Einseitig")
        self.simplex_radio.show()
        self.simplex_radio.connect('toggled', self.checkbox_changed, None)
        #self.simplex_radio.set_active(True)
        self.long_edge_radio = gtk.RadioButton(self.simplex_radio, "Doppelseitig (lange Seite)")
        self.long_edge_radio.show()
        self.long_edge_radio.connect('toggled', self.checkbox_changed, None)
        self.short_edge_radio = gtk.RadioButton(self.simplex_radio, "Doppelseitig (kurze Seite)")
        self.short_edge_radio.show()
        self.short_edge_radio.connect('toggled', self.checkbox_changed, None)
        self.bw_checkbox.connect('toggled', self.checkbox_changed, None)
        vbox.pack_start(self.simplex_radio)
        vbox.pack_start(self.long_edge_radio)
        vbox.pack_start(self.short_edge_radio)
        vbox.pack_start(self.bw_checkbox)
        vbox.show()
        frm.add(vbox)
        frm.show()
        self.vbox.pack_start(frm)

        # button
        self.action_button = gtk.Button(
                label="Berechnen"
            )
        self.action_button.child.set_use_markup(True)
        self.action_button.connect('clicked', self.do_action, None)
        self.action_button.show()
        self.vbox.pack_start(self.action_button)

        # add main hbox
        self.win.add(self.vbox)

        self.apply_state()

        # show window
        self.vbox.show()
        self.win.show()

    def file_selected(self, btn, data):
        self.file = btn.get_filename()
        if self.file:
            self.state = 'count'
        self.apply_state()

    def load_uploaded(self, btn, data):
        nonce = self.pin_input.get_text()
        f = UploadedFile(nonce)
        f.parse()
        self.file = f.results['filename']
        if f.results['duplex'] == '1':
            self.duplex = 'long'
        if f.results['blackwhite'] == '1':
            self.blackwhite = True
        self.state = 'count'
        p = f.get_price()
        self.apply_state()
        if p:
            self.price = p
            self.state = 'print'
            self.apply_state()


    def checkbox_changed(self, btn, data):
        if self.simplex_radio.get_active():
            self.duplex = None
        elif self.long_edge_radio.get_active():
            self.duplex = 'long'
        elif self.short_edge_radio.get_active():
            self.duplex = 'short'

        self.blackwhite = self.bw_checkbox.get_active()
        if self.state:
            self.state = 'count'
        self.apply_state()

    def do_action(self, btn, data):
        if self.state == 'count':
            self.state = 'progress'
            self.apply_state()
            self.do_count()
        elif self.state == 'print':
            self.state = None
            self.apply_state()
            self.do_print()

    def timer_event(self, *args, **kwargs):
        self.apply_state()
        if self.count_proc:
            #self.price_buffer += self.count_proc.stdout.read()
            #print "DEBUG: timer_event: buffer = %s, retcode = %s" % (repr(self.price_buffer), repr(self.count_proc.returncode))
            #print "DEBUG: poll says: %s" % repr(self.count_proc.poll())
            if self.count_proc.poll() != None:
                self.state = 'print'
                #self.price = float(self.price_buffer)
                self.price = float(self.count_proc.stdout.read())
                self.apply_state()
                return False
        else:
            return False

        return True # call me again

    def get_billing_string(self):
        return (self.blackwhite and "black" or "color") + "_" + (self.duplex and "duplex" or "simplex")

    def do_count(self):
        gobject.timeout_add_seconds(1, self.timer_event, None)
        self.price_buffer = ""
        self.kill_subproc()
        self.count_proc = subprocess.Popen(
                (
                    PRICE_CMD,
                    'pricecalc',
                    self.get_billing_string(),
                    self.file,
                    'stdout'
                ),
                bufsize=(1024*16),
                stdout=subprocess.PIPE
            )

    def kill_subproc(self):
        try:
            if self.count_proc:
                self.count_proc.terminate()
                self.count_proc = None
        except:
            pass
    
    def do_print(self):
        duplex = 'None'
        if self.duplex == 'long':
            duplex = 'DuplexNoTumble'
        elif self.duplex == 'short':
            duplex = 'DuplexTumble'

        color = 'CMYK'
        if self.blackwhite:
            color = 'Gray'

        subprocess.Popen(
                (
                    '/usr/bin/lp',
                    '-o', "Duplex=%s" % duplex,
                    '-o', "ColorModel=%s" % color,
                    '-o', "job-billing=%s" % self.get_billing_string(),
                    self.file
                )
            )
        self.state = None
        self.open_button.unselect_all()
        self.file = None
        self.duplex = None
        self.blackwhite = False
        self.apply_state()

    def apply_state(self):
        """Modify widgets based on self.state"""
        print("DEBUG: state = %s" % repr(self.state))

        if self.state != 'progress':
            self.kill_subproc()

        # set filename
        if self.file:
            self.open_button.set_filename(self.file)
        if self.duplex == 'long':
            self.long_edge_radio.set_active(True)
        elif self.duplex == 'short':
            self.short_edge_radio.set_active(True)
        else:
            self.simplex_radio.set_active(True)
  
        self.bw_checkbox.set_active(self.blackwhite)

        # set state of button
        if self.state == 'count' or self.state == 'print':
            self.action_button.set_sensitive(True)
        else:
            self.action_button.set_sensitive(False)

        # set label of button
        if self.state == None or self.state == 'count':
            self.action_button.set_label('Berechnen')
        elif self.state == 'progress':
            if self.progress_state:
                self.action_button.set_label('Bitte warten...')
                self.progress_state = False
            else:
                self.action_button.set_label('Berechnung läuft...')
                self.progress_state = True
        elif self.state == 'print':
            self.action_button.child.set_markup("Drucken für <b>%0.2f EUR</b>" % self.price)
        else:
            raise "State engine damaged, invalid state = %s" % repr(self.state)

    def quit(self, *args, **kwargs):
        """Quit the mainloop."""
        self.kill_subproc()
        gtk.main_quit()

    def main(self):
        """Start GTK mainloop."""
        gtk.main()

if __name__ == '__main__':
    a = PrinterGui()
    a.main()
