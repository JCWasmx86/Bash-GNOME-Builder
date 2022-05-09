#!/usr/bin/env python3
import os
import gi
import sys

from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gio
from gi.repository import Ide

SEVERITY_MAP = {
	"warning": Ide.DiagnosticSeverity.WARNING,
	"error": Ide.DiagnosticSeverity.ERROR,
	"note": Ide.DiagnosticSeverity.NOTE,
}

class BashtoolsDiagnosticProvider(Ide.DiagnosticTool):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.set_program_name('shellcheck')

	def do_configure_launcher(self, launcher, file, contents, lang_id):
		launcher.push_argv('--format=gcc')
		launcher.push_argv('-')

	def do_populate_diagnostics(self, diagnostics, file, stdout, stderr):
		try:
			for line in stdout.splitlines():
				parts = line.split(" ", 2)
				raw_loc = parts[0].split(":")
				start = Ide.Location.new(file, int(raw_loc[1]) - 1, int(raw_loc[2]))
				severity = SEVERITY_MAP[parts[1].replace(":", "")]
				diagnostic = Ide.Diagnostic.new(severity, parts[2], start)
				diagnostics.add(diagnostic)
		except Exception as e:
			Ide.warning('Failed to deserialize diagnostics: {}'.format(e))

class BashtoolsFormatter(Ide.Object, Ide.Formatter):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	def do_load(self):
		pass

	def do_format_finish(self, result):
		return True

	def do_format_async(self, buffer, options, cancellable, callback, user_data):
		task = Ide.Task.new(self,cancellable, callback)
		task.set_priority(GLib.PRIORITY_HIGH)
		task.set_name('Formatting script using shfmt')
		args = ['/usr/bin/shfmt', '-i', str(options.get_tab_width()) if options.get_insert_spaces() else '0', '-', None]
		launcher = Ide.SubprocessLauncher ()
		launcher.set_cwd("/")
		launcher.set_run_on_host (True)
		launcher.set_flags(Gio.SubprocessFlags.STDIN_PIPE | Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE)
		launcher.push_args(('shfmt', '-i', str(options.get_tab_width()) if options.get_insert_spaces() else '0', '-'))
		proc = launcher.spawn()
		success, stdout, stderr = proc.communicate_utf8(buffer.dup_content().get_data().decode("UTF-8"), cancellable)
		proc.wait()
		n_lines = buffer.get_line_count()
		n_columns = len(buffer.get_line_text (n_lines))
		buffer.begin_user_action()
		buffer.delete(buffer.get_start_iter(), buffer.get_end_iter())
		buffer.insert(buffer.get_start_iter(), stdout)
		buffer.end_user_action()
		task.return_boolean(True)
