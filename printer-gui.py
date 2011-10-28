#!/usr/bin/python
# vim: set fileencoding=utf-8 st=4 sts=4 et:

PRICE_CMD = '/home/roman/Git/ssn-printer-gui/price-dummy'
PRINT_CMD = '/home/roman/Git/ssn-printer-gui/print-dummy'

import subprocess

import pygtk
pygtk.require('2.0')
import gtk
import gobject

class PrinterGui:
    # file to print
    file = None

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
        
        # create central vbox
        self.vbox = gtk.VBox(homogeneous=False, spacing=0)

        # ensure proper end of application
        self.win.connect('delete_event', lambda w, e: gtk.main_quit())
        self.win.connect('destroy', self.quit)

        # file chooser button
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
        self.vbox.pack_start(self.open_button)

        # duplex and b/w checkboxes
        self.bw_checkbox = gtk.CheckButton(label="Schwarz / Weiss")
        self.duplex_checkbox = gtk.CheckButton(label="Duplex")
        self.bw_checkbox.show()
        self.duplex_checkbox.show()
        self.vbox.pack_start(self.bw_checkbox)
        self.vbox.pack_start(self.duplex_checkbox)

        # button
        self.action_button = gtk.Button(
                label="Berechnen"
            )
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

        return True # call me again

    def do_count(self):
        gobject.timeout_add_seconds(1, self.timer_event, None)
        self.price_buffer = ""
        self.count_proc = subprocess.Popen(
                (PRICE_CMD, self.file),
                bufsize=(1024*16),
                stdout=subprocess.PIPE
            )
    
    def do_print(self):
        subprocess.Popen((PRINT_CMD, self.file))

    def apply_state(self):
        """Modify widgets based on self.state"""
        print("DEBUG: state = %s" % repr(self.state))
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
            self.action_button.set_label("Drucken für <b>%0.2f EUR</b>" % self.price)
        else:
            raise "State engine damaged, invalid state = %s" % repr(self.state)

        if self.state == None:
            #self.open_button.set_filename("")
            self.open_button.unselect_all()

    def quit(self, *args, **kwargs):
        """Quit the mainloop."""
        gtk.main_quit()

    def main(self):
        """Start GTK mainloop."""
        gtk.main()

if __name__ == '__main__':
    a = PrinterGui()
    a.main()
