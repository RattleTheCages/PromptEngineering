#
#           QK      -- An awesome AI editor
#
# The QK Editor is AI assistance that offers a fully functioning editor.
# With qk ;), expect AI to do the editing, not you.
# Prompt AI to write, edit, and code in the bottom panel.
# Enter and edit text manually in the top panel.
# Choose the viewpoint, the type of AI assistance you'd like, such as Grammar, Spelling, or computer Coding.
# In the freestyle viewpoint, one can enter any question or content.
# This work is copyright, Daniel Huffman, pen name Rattle. All rights reserved.

import sys

import os
import re
import json
import argparse
import curses
import signal

import subprocess
import QKCogEngine

qk_version = 'ver 1.01.01'
parser = argparse.ArgumentParser()
parser.add_argument('session', nargs='?', default="qkAi.txt")
args = parser.parse_args()

class EditRevisionManager:
    def __init__(self, session_name_with_suffix, cogengine):
        self.revisions = {}
        self.subrevisions = {}
        self.subrev_type = 'Original'
        self.subrev_num = 0
        self.subrev_being_viewed = 0
        self.original_filename = session_name_with_suffix
        self.session_name, self.session_suffix = os.path.splitext(session_name_with_suffix)
        self.rev_num = self.find_latest_file_rev_num() + 1
        self.cog_filename = f'{self.session_name}.{self.rev_num}.cog.json'
        self.cogengine = cogengine
        self.edit_filename = f'{self.session_name}.{self.rev_num}{self.session_suffix}'
        self.pmt_filename = f'{self.session_name}.{self.rev_num}.pmt'
        self.pmt_summary = ""
    def store_revision(self, rev_num, text):
        self.revisions[rev_num] = list(map(str, text))
    def get_revision(self, rev_num):
        return self.revisions.get(rev_num, [])
    def get_latest_revision(self):
        if self.revisions:
            max_rev_num = max(self.revisions.keys())
            return self.revisions[max_rev_num]
        return []
    def store_subrevision(self, subrev_text, subrev_pmt, subrev_type):
        self.subrev_num += 1
        self.subrev_type = subrev_type
        self.subrevisions[self.subrev_num] = {
            "text": list(map(str, subrev_text)),
            "pmt": list(map(str, subrev_pmt)),
            "type": subrev_type
        }
        subrev_filename = f'{self.session_name}.{self.rev_num}.{self.subrev_num}.subrev'
        with open(subrev_filename, 'w') as f:
            f.write(f"Subrevision Type: {subrev_type}\n")
            f.write("Subrevision Text:\n")
            for line in subrev_text:
                if isinstance(line, list):
                    f.write(''.join(line) + '\n')
                else:
                    f.write(line + '\n')
            f.write("\nSubrevision Context:\n")
            for line in subrev_pmt:
                if isinstance(line, list):
                    f.write(''.join(line) + '\n')
                else:
                    f.write(line + '\n')
    def get_subrevision_text(self, subrev_num):
        self.subrev_being_viewed = subrev_num
        subrevision = self.subrevisions.get(subrev_num)
        if subrevision:
            return subrevision.get("text")
        else:
            subrev_num = 0
            self.subrev_being_viewed = subrev_num
            subrevision = self.subrevisions.get(subrev_num)
    def find_latest_file_rev_num(self):
        files = os.listdir('.')
        suffixes = [self.session_suffix, '.cog.json', '.pmt']
        pattern = re.compile(rf'{re.escape(self.session_name)}\.(\d+)(?:{re.escape(self.session_suffix)}|\.cog\.json|\.pmt)')
        max_rev = 0
        for file in files:
            for suffix in suffixes:
                if file.endswith(suffix):
                    match = re.match(rf'{re.escape(self.session_name)}\.(\d+)', file)
                    if match:
                        rev_num = int(match.group(1))
                        max_rev = max(max_rev, rev_num)
        return max_rev
    def increment_rev(self):
        self.rev_num = self.find_latest_file_rev_num() + 1
        self.cog_filename = f'{self.session_name}.{self.rev_num}.cog.json'
        self.edit_filename = f'{self.session_name}.{self.rev_num}{self.session_suffix}'
        self.pmt_filename = f'{self.session_name}.{self.rev_num}.pmt'
    def write_file(self, viewpoint, edit_panel_content, command_panel_content):
        self.increment_rev()
        self.store_revision(self.rev_num, edit_panel_content)
        if os.path.exists(self.original_filename):
            os.rename(self.original_filename, self.edit_filename + ".org")
        try:
            with open(self.original_filename, 'w') as og:
                for line in edit_panel_content:
                    og.write(line + '\n')
            with open(self.edit_filename, 'w') as f:
                for line in edit_panel_content:
                    f.write(line + '\n')
            with open(self.pmt_filename, 'a') as pmtf:
                for line_num, line in enumerate(command_panel_content, start=1):
                    self.write_pmt_file_line(line, line_num, viewpoint, 'Write')
                pmtf.write(f"[Context Summary] {self.pmt_summary}\n")
        except Exception as e:
            return "no wr"
        finally:
            return "wrote"
    def read_file(self):
        try:
            with open(self.original_filename, 'r') as og:
                lines = [line.rstrip('\n') for line in og]
            return "read ", lines
        except Exception as e:
            if isinstance(e, PermissionError):
                return "denid",
            elif isinstance(e, IsADirectoryError):
                return "dir  "
    def write_pmt_file_line(self, line, line_num, viewpoint, action):
        with open(self.pmt_filename, 'a') as pmtf:
            pmtf.write(f"{line_num:03}<[{viewpoint.get_current_name()}][{action}]{line}\n")
    def update_pmt_summary(self, viewpoints):
        if 'Inline' in viewpoints.get_textops():
            return
        pmt_entries = self.pmt_subrev_entries()
        if not pmt_entries or len(pmt_entries) < 0:
            return
        self.cogengine.reset_viewpoint(viewpoints, "Pmt_Summary")
        #self.cogengine.add_usermsg(pmt_entries)
        for line in self.pmt_subrev_entries():
            self.cogengine.add_cogtext("user", line)
        self.cogengine.save_cogtext()
        summary = self.cogengine.ai_query(viewpoints)
        self.pmt_summary = summary.choices[0].message.content[:96]
    def get_revision_display(self, viewpoints):
        subrevision = self.subrevisions.get(self.subrev_being_viewed, {})
        subrev_type = subrevision.get("type", "Session")
        if self.pmt_summary == "":
            self.pmt_summary = "Hello!  I am QK ;)  Your AI assisted editor.  How can I help?"
        return f"Session: {self.original_filename}  Revision: {self.rev_num}  Sub_rev: {self.subrev_being_viewed}  Sub_type: {subrev_type}    Context Summary: {self.pmt_summary}"
    def find_highest_markup_subrevision(self):
        highest_subrev_num = -1
        subrev_text = None
        for subrev_num, subrevision in self.subrevisions.items():
            if subrevision.get("type") == "Markup":
                if subrev_num > highest_subrev_num:
                    highest_subrev_num = subrev_num
                    subrev_text = subrevision.get("text")
        self.subrev_being_viewed = highest_subrev_num
        return subrev_text
    def find_highest_replace_subrevision(self):
        highest_subrev_num = -1
        subrev_text = None
        for subrev_num, subrevision in self.subrevisions.items():
            if subrevision.get("type") == "Replace":
                if subrev_num > highest_subrev_num:
                    highest_subrev_num = subrev_num
                    subrev_text = subrevision.get("text")
        self.subrev_being_viewed = highest_subrev_num
        return subrev_text
    def pmt_subrev_entries(self):
        pmt_entries = {}
        for subrev_num, subrev in self.subrevisions.items():
            subrev_type = subrev.get("type", "unknown")
            if subrev_type not in pmt_entries:
                pmt_entries[subrev_type] = []
            if 'pmt' in subrev:
                pmt_entries[subrev_type].extend(subrev['pmt'])
        pmt_entries_str = ""
        for subrev_type, entries in pmt_entries.items():
            pmt_entries_str += "\n".join(entries)
        return pmt_entries_str

class QKEditor:
    def __init__(self, stdscr):
        signal.signal(signal.SIGINT, self.handle_sigint)
        self.stdscr = stdscr
        self.mode = 'line'
        self.status = 'hello'
        self.clipboard = []
        self.yanked_lines = set()
        self.yank_mode_active = 'off'
        self.del_lines = set()
        self.context_panel = 1
        self.show_left_column = True
        self.search_results = []
        self.current_search_result = -1
        self.panels = [
            {"line_num": 0, "col_num": 0, "text": [""]},
            {"line_num": 0, "col_num": 0, "text": [""]},
        ]
        self.panel_offsets = [0, 0]
        self.screen_height, self.screen_width = self.stdscr.getmaxyx()
        if self.screen_height < 32:
            self.bottom_panel_size = self.screen_height // 4
            self.top_panel_size = self.screen_height - self.bottom_panel_size
        else:
            self.bottom_panel_size = 16
            self.top_panel_size = self.screen_height - self.bottom_panel_size - 1
        self.viewpoints = QKCogEngine.Viewpoints()
        self.load_viewpoints()
        self.personalchoice = self.viewpoints.get_current_name()
        self.context = QKCogEngine.QKCogEngine(self.viewpoints)
        self.revision_manager = EditRevisionManager(args.session, self.context)
        self.keymap = {
            ord('\\'): self.handle_backslash,
            ord('\n'): self.handle_return,
            11: self.handle_ctrl_k,
            23: self.write_file,
            18: self.read_file,
            1: self.handle_ctrl_a,
            16: self.handle_ctrl_p,
            6: self.search_text,
            22: self.handle_ctrl_v,
            2: self.prev_search_result,
            4: self.delete_current_line,
            20: self.handle_ctrl_t,
            25: self.handle_ctrl_y,
            24: self.handle_ctrl_x,
            8: self.handle_ctrl_h,
            7: self.handle_ctrl_g,
            14: self.handle_ctrl_n,
            21: self.handle_ctrl_u,
            5: self.handle_ctrl_e,
            17: self.handle_ctrl_q,
            19: self.handle_ctrl_s,
            #127: lambda: self.handle_backspace(127),
            curses.KEY_BACKSPACE: lambda: self.handle_backspace(curses.KEY_BACKSPACE),
            curses.KEY_UP: self.handle_up_arrow,
            curses.KEY_DOWN: self.handle_down_arrow,
            curses.KEY_RIGHT: self.handle_right_arrow,
            curses.KEY_LEFT: self.handle_left_arrow,
            curses.KEY_DC: self.handle_del_key,
            curses.KEY_END: self.handle_end_key,
            curses.KEY_HOME: self.handle_home_key
            #43: self.increase_top_panel_size,
            #45: self.decrease_top_panel_size,
        }
        if os.path.exists(args.session):
            self.read_file(args.session)
        else:
            self.show_splash_screen()
    def handle_return(self):
        line = self.panels[self.context_panel]["text"][self.panels[self.context_panel]["line_num"]]
        self.context.add_usermsg(line)
        self.panels[self.context_panel]["text"].insert(self.panels[self.context_panel]["line_num"] + 1, self.panels[self.context_panel]["text"][self.panels[self.context_panel]["line_num"]][self.panels[self.context_panel]["col_num"]:])
        self.panels[self.context_panel]["text"][self.panels[self.context_panel]["line_num"]] = self.panels[self.context_panel]["text"][self.panels[self.context_panel]["line_num"]][:self.panels[self.context_panel]["col_num"]]
        self.panels[self.context_panel]["line_num"] += 1
        self.panels[self.context_panel]["col_num"] = 0
        self.adjust_panel_offset()
    def display(self):
        modeOrStatus = self.mode
        if self.status != "":
            modeOrStatus = self.status
            self.status = ""
        top_panel = self.panels[0]["text"]
        bottom_panel = self.panels[1]["text"]
        self.stdscr.clear()
        for y in range(min(self.top_panel_size, len(top_panel) - self.panel_offsets[0])):
            line = top_panel[y + self.panel_offsets[0]]
            line = line[:self.screen_width]
            highlight = curses.A_UNDERLINE if self.context_panel == 0 and y + self.panel_offsets[0] in self.yanked_lines else curses.A_NORMAL
            try:
                if self.show_left_column:
                    left_column = f"{((y + self.panel_offsets[0] + 1) % 1000):03}<{modeOrStatus:5}>"
                    self.stdscr.addstr(y, 0, left_column, highlight | curses.A_REVERSE | (curses.A_BOLD if (self.context_panel == 0 and y + self.panel_offsets[0] == self.panels[0]["line_num"]) else 0))
                    start_text_pos = len(left_column)
                else:
                    start_text_pos = 0
                if self.context_panel == 0 and y + self.panel_offsets[0] == self.panels[0]["line_num"]:
                    for x, ch in enumerate(line):
                        if x == self.panels[0]["col_num"]:
                            self.stdscr.addch(y, start_text_pos + x, ch, curses.A_REVERSE | curses.A_NORMAL)
                        else:
                            self.stdscr.addch(y, start_text_pos + x, ch, curses.A_BOLD)
                    if self.panels[0]["col_num"] == len(line):
                        self.stdscr.addch(y, start_text_pos + self.panels[0]["col_num"], ' ', curses.A_REVERSE | curses.A_NORMAL)
                    if self.context_panel == 0:
                        self.stdscr.move(y, start_text_pos + self.panels[0]["col_num"])
                else:
                    self.stdscr.addstr(y, start_text_pos, line)
            except curses.error:
                pass
        for y in range(self.top_panel_size, self.top_panel_size + self.bottom_panel_size):
            if y - self.top_panel_size >= len(bottom_panel) - self.panel_offsets[1]:
                break
            highlight = curses.A_UNDERLINE if self.context_panel == 1 and y - self.top_panel_size + self.panel_offsets[1] in self.yanked_lines else curses.A_NORMAL
            line = bottom_panel[y - self.top_panel_size + self.panel_offsets[1]]
            line = line[:self.screen_width]
            try:
                if self.show_left_column:
                    left_column = f"{((y - self.top_panel_size + self.panel_offsets[1] + 1) % 1000):03}<{self.viewpoints.get_current_name():5}>"
                    self.stdscr.addstr(y, 0, left_column, highlight | curses.A_REVERSE | (curses.A_BOLD if (self.context_panel == 1 and y - self.top_panel_size + self.panel_offsets[1] == self.panels[1]["line_num"]) else 0))
                    start_text_pos = len(left_column)
                else:
                    start_text_pos = 0
                if self.context_panel == 1 and y - self.top_panel_size + self.panel_offsets[1] == self.panels[1]["line_num"]:
                    for x, ch in enumerate(line):
                        if x == self.panels[1]["col_num"]:
                            self.stdscr.addch(y, start_text_pos + x, ch, curses.A_REVERSE | curses.A_NORMAL)
                        else:
                            self.stdscr.addch(y, start_text_pos + x, ch, curses.A_BOLD)
                    if self.panels[1]["col_num"] == len(line):
                        self.stdscr.addch(y, start_text_pos + self.panels[1]["col_num"], ' ', curses.A_REVERSE | curses.A_NORMAL)
                    if self.context_panel == 1:
                        self.stdscr.move(y, start_text_pos + self.panels[1]["col_num"])
                else:
                    self.stdscr.addstr(y, start_text_pos, line)
            except curses.error:
                pass
        summary_str = self.revision_manager.get_revision_display(self.viewpoints)
        max_len = self.screen_width - 1
        if len(summary_str) > max_len:
            summary_str = summary_str[:max_len]
        try:
            self.stdscr.addstr(self.screen_height - 1, 0, summary_str)
        except curses.error:
            pass
        self.stdscr.refresh()
    def adjust_panel_offset(self):
        for i in range(2):
            if self.panels[i]["line_num"] is None:
                self.panels[i]["line_num"] = 0
            while self.panels[i]["line_num"] < self.panel_offsets[i]:
                self.panel_offsets[i] -= 1
            while self.panels[i]["line_num"] >= self.panel_offsets[i] + (self.top_panel_size if i == 0 else self.bottom_panel_size):
                self.panel_offsets[i] += 1
    def increase_top_panel_size(self):
        if self.top_panel_size + self.bottom_panel_size < curses.LINES:
            self.top_panel_size += 1
            self.bottom_panel_size -= 1
            self.adjust_panel_offset()
    def decrease_top_panel_size(self):
        if self.bottom_panel_size + self.top_panel_size > 1:
            self.top_panel_size -= 1
            self.bottom_panel_size += 1
            self.adjust_panel_offset()
    def insert_char(self, ch):
        line = self.panels[self.context_panel]["text"][self.panels[self.context_panel]["line_num"]]
        if ch in (curses.KEY_BACKSPACE, 127):
            if self.panels[self.context_panel]["col_num"] > 0:
                self.panels[self.context_panel]["text"][self.panels[self.context_panel]["line_num"]] = line[:self.panels[self.context_panel]["col_num"] - 1] + line[self.panels[self.context_panel]["col_num"]:]
                self.panels[self.context_panel]["col_num"] -= 1
            elif self.panels[self.context_panel]["col_num"] == 0 and self.panels[self.context_panel]["line_num"] > 0:
                prev_line = self.panels[self.context_panel]["text"][self.panels[self.context_panel]["line_num"] - 1]
                self.panels[self.context_panel]["col_num"] = len(prev_line)
                self.panels[self.context_panel]["text"][self.panels[self.context_panel]["line_num"] - 1] += self.panels[self.context_panel]["text"].pop(self.panels[self.context_panel]["line_num"])
                self.panels[self.context_panel]["line_num"] -= 1
        elif 0 <= ch <= 0x10FFFF and chr(ch).isprintable():
            self.mode = 'edit'
            self.panels[self.context_panel]["text"][self.panels[self.context_panel]["line_num"]] = line[:self.panels[self.context_panel]["col_num"]] + chr(ch) + line[self.panels[self.context_panel]["col_num"]:]
            self.panels[self.context_panel]["col_num"] += 1
        self.adjust_panel_offset()
    def handle_backspace(self, ch):
        if self.mode == 'edit':
            self.insert_char(ch)
        else:
            if self.clipboard:
                self.swap_clipboard_with_panel_text()
                self.toggle_undo_redo_status()
                self.constrain_cursor_within_panel()
                self.adjust_panel_offset()
    def swap_clipboard_with_panel_text(self):
        undo_content = list(self.panels[self.context_panel]["text"])
        self.panels[self.context_panel]["text"].clear()
        self.panels[self.context_panel]["text"].extend(self.clipboard)
        self.clipboard = undo_content
    def toggle_undo_redo_status(self):
        self.status = 'redo' if self.status == 'undo' else 'undo'
        self.display()
    def constrain_cursor_within_panel(self):
        panel = self.panels[self.context_panel]
        panel["line_num"] = max(0, min(panel["line_num"], len(panel["text"]) - 1))
        panel["col_num"] = max(0, min(panel["col_num"], len(panel["text"][panel["line_num"]])))
    def handle_up_arrow(self):
        if self.panels[self.context_panel]["line_num"] > 0:
            self.panels[self.context_panel]["line_num"] -= 1
            if self.panels[self.context_panel]["col_num"] > len(self.panels[self.context_panel]["text"][self.panels[self.context_panel]["line_num"]]):
                self.panels[self.context_panel]["col_num"] = len(self.panels[self.context_panel]["text"][self.panels[self.context_panel]["line_num"]])
            self.adjust_panel_offset()
    def handle_down_arrow(self):
        if self.panels[self.context_panel]["line_num"] < len(self.panels[self.context_panel]["text"]) - 1:
            self.panels[self.context_panel]["line_num"] += 1
            if self.panels[self.context_panel]["col_num"] > len(self.panels[self.context_panel]["text"][self.panels[self.context_panel]["line_num"]]):
                self.panels[self.context_panel]["col_num"] = len(self.panels[self.context_panel]["text"][self.panels[self.context_panel]["line_num"]])
            self.adjust_panel_offset()
    def handle_right_arrow(self):
        line = self.panels[self.context_panel]["text"][self.panels[self.context_panel]["line_num"]]
        if self.panels[self.context_panel]["col_num"] < len(line):
            self.panels[self.context_panel]["col_num"] += 1
        self.mode = 'edit'
    def handle_left_arrow(self):
        if self.panels[self.context_panel]["col_num"] > 0:
            self.panels[self.context_panel]["col_num"] -= 1
        self.mode = 'edit'
    def handle_backslash(self):
                if 'Coder' in self.viewpoints.get_role():
                    self.context_panel = 0
                if self.viewpoints.get_current_name() == 'Freestyle':
                    self.context_panel = 0
                self.context.reset(self.viewpoints)
                if self.viewpoints.test_textop('Inline'):
                    user_line = self.panels[self.context_panel]["text"][self.panels[self.context_panel]["line_num"]].strip()
                    self.context.add_cogtext("user", user_line)
                    #self.revision_manager.write_pmy_file_line(user_line, self.panels[self.context_panel]["line_num"], self.viewpoints, 'Query')
                else:
                    self.write_file()
                    self.revision_manager.store_subrevision(self.panels[0]["text"], self.panels[1]["text"], "Original")
                    self.status = 'ai *'
                    self.display()
                    self.revision_manager.update_pmt_summary(self.viewpoints)
                    self.mode = 'ai *'
                    self.display()
                    self.context.reset(self.viewpoints)
                    userlines_user = ""
                    if self.yank_mode_active == 'yank' and self.yanked_lines:
                        marked_lines = [self.panels[0]["text"][line] for line in sorted(self.yanked_lines)]
                        #userlines_user = "\n<-><-><-><Please find below the highlighted text for you to consider.><-><-><->\n"
                        #userlines_user += "\n".join(marked_lines)
                        #userlines_user += "\n<-><-><-><Please find above the highlighted text.><-><-><->\n"
                        self.context.add_cogtext("user", "<-><-><-><Please find below the highlighted text for you to consider.><-><-><->")
                        for line in marked_lines:
                            self.context.add_cogtext("user", line)
                        self.context.add_cogtext("user", "<-><-><-><Please find above the highlighted text.><-><-><->\n")
                        self.yanked_lines.clear()
                        self.yank_mode_active = 'off'
                    userlines_user += "\n".join(line for line in self.panels[0]["text"] if line.strip())
                    userlines_system = "\n".join(line for line in self.panels[1]["text"] if line.strip())
                    #self.context.add_cogtext("system", userlines_system)
                    #self.context.add_cogtext("user", userlines_user)
                    for line in self.panels[1]["text"]:
                        if line.strip():
                            self.context.add_cogtext("system", line)
                    for line in self.panels[0]["text"]:
                        if line.strip():
                            self.context.add_cogtext("user", line)
                if self.context_panel == 1:
                    if not self.viewpoints.test_textop('Inline'):
                        userlines = "\n".join(line for line in self.panels[1]["text"] if line.strip())
                        self.context.add_cogtext("user", userlines)
                    else:
                        if not self.viewpoints.test_textop('Inline'):
                            userlines_system = "\n".join(line for line in self.panels[1]["text"] if line.strip())
                            userlines_user = "n".join(line for line in self.panels[0]["text"] if line.strip())
                            self.context.add_cogtext("system", userlines_system)
                            self.context.add_cogtext("user", userlines_user)
                self.context.save_cogtext()
                self.clipboard = [line for line in self.panels[self.context_panel]["text"]]
                # I am a fluffy unicorn, with light green spots.
                ai_revise = self.context.ai_query(self.viewpoints)
                self.context.save_cogtext()
                self.apply_textops(ai_revise, self.viewpoints.get_textops())
                self.mode = 'reply'
                self.stdscr.nodelay(True)
                try:
                    ch = self.stdscr.getch()
                    while ch != -1:
                        ch = self.stdscr.getch()
                finally:
                    self.stdscr.nodelay(False)
                self.adjust_panel_offset()
    def apply_textops(self, ai_revise, textops):
        response_text = ai_revise.choices[0].message.content.split('\n')
        if 'Inline' in textops:
            current_line_number = self.panels[self.context_panel]["line_num"]
            #self.revision_manager.write_pmy_file_line(response_text[0], current_line_number, self.viewpoints, 'Reply')
            self.insert_as_current_line(response_text[0])
        #else:
        #    self.revision_manager.store_subrevision(self.panels[0]["text"], self.panels[1]["text"], "Original")
        if 'Coder' in self.viewpoints.get_role():
            if 'python' in self.viewpoints.get_decoms():
                python_objs = self.context.extract_python_objects(ai_revise.choices[0].message.content)
                for tx_op in textops:
                    markedup_code = self.refactor_edit_panel(response_text, python_objs, tx_op)
                    self.revision_manager.store_subrevision(markedup_code, self.panels[1]["text"], tx_op)
                sub_text = self.revision_manager.find_highest_markup_subrevision()
            if 'cpp' in self.viewpoints.get_decoms():
                cpp_objs = self.context.extract_cpp_objects(ai_revise.choices[0].message.content)
                #self.revision_manager.store_subrevision(response_text, self.panels[1]["text"], "Replace")
                #commented_text = [f"// {line}" for line in response_text]
                #self.panels[self.context_panel]["text"] = commented_text
                for tx_op in textops:
                    markedup_code = self.refactor_cpp_edit_panel(response_text, cpp_objs, tx_op)
                    self.revision_manager.store_subrevision(markedup_code, self.panels[1]["text"], tx_op)
                sub_text = self.revision_manager.find_highest_replace_subrevision()
            if sub_text:
                self.panels[0]["col_num"] = 0
                self.panels[0]["text"] = sub_text
            self.search_offset()
        elif 'Replace' in textops:
            self.panels[self.context_panel]["text"] = response_text
            self.revision_manager.store_subrevision(response_text, self.panels[1]["text"], "Replace")
        elif 'Concatenate' in textops:
            bline = len(self.panels[self.context_panel]["text"])
            self.panels[self.context_panel]["line_num"] = bline
            self.insert_lines_at_current_line("'''")
            self.insert_lines_at_current_line(f"[{self.viewpoints.get_current_name()}][AI viewpoint][--Concatenate]")
            self.panels[self.context_panel]["text"].extend(response_text)
            self.panels[self.context_panel]["text"].append('\n')
            #self.panels[self.context_panel]["line_num"] = len(self.panels[self.context_panel]["text"]) - 1
            #self.panels[self.context_panel]["col_num"] = len(self.panels[self.context_panel]["text"][self.panels[self.context_panel]["line_num"]])
            self.insert_lines_at_current_line(" ")
            self.insert_lines_at_current_line("'''")
            self.panels[self.context_panel]["line_num"] = bline
            self.revision_manager.store_subrevision(response_text, self.panels[1]["text"], "Concatenate")
            self.panels[self.context_panel]["col_num"] = 0
            self.search_offset()
    def refactor_edit_panel(self, response_text, objects, textops):
                top_panel_copy = self.panels[0]["text"][:]
                cursor_pos = 0
                if 'Refactor' in textops or 'Deprecate' in textops:
                    for function in objects:
                        func_name = function['name']
                        func_code = function['code']
                        object_name = function.get('object', None)
                        matched_class = None
                        insert_pos = None
                        end_pos = None
                        for x, line in enumerate(top_panel_copy):
                            if object_name and line.strip().startswith(f"class {object_name}"):
                                matched_class = object_name
                            if matched_class == object_name and func_name in line and re.match(r'^\s*def\b', line):
                                indent_level = len(line) - len(line.lstrip())
                                indent = ' ' * indent_level
                                insert_pos = x
                                for y, end_line in enumerate(top_panel_copy[x+1:], start=x+1):
                                    if re.match(r'^\s*(def|class)\b', end_line):
                                        end_pos = y
                                        break
                                if end_pos is None:
                                    end_pos = len(top_panel_copy)
                                commented_code = [f"{indent}''' [{self.viewpoints.get_current_name()} --Deprecate][{object_name}::{func_name}][Rev:{self.revision_manager.rev_num} Sub:{self.revision_manager.subrev_num+1}][Type: Deprecate]"] + [l for l in top_panel_copy[insert_pos:end_pos]] + [f"{indent}'''"]
                                refactored_code = []
                                if 'Deprecate' in textops:
                                    refactored_code = [f"{indent}# [{self.viewpoints.get_current_name()} --Refactor][{object_name}::{func_name}][Rev:{self.revision_manager.rev_num} Sub:{self.revision_manager.subrev_num+1}][Type: Deprecate]\n"]
                                for l in func_code.split('\n'):
                                    if 'def' in l:
                                        refactored_code += [indent + l]
                                    else:
                                        refactored_code += [l]
                                if 'Deprecate' in textops:
                                    top_panel_copy = (
                                        top_panel_copy[:insert_pos] +
                                        commented_code + refactored_code +
                                        top_panel_copy[end_pos:]
                                    )
                                if 'Refactor' in textops:
                                    top_panel_copy = (
                                        top_panel_copy[:insert_pos] +
                                        refactored_code +
                                        top_panel_copy[end_pos:]
                                    )
                                break
                        if insert_pos is None and not object_name:
                            indent = ' ' * 4
                            new_code = []
                            new_code += [indent + l for l in func_code.split('\n')]
                            top_panel_copy.extend([f"\n''' [{self.viewpoints.get_current_name()}[--new]\n'''", new_code, ""])
                if 'Markup' in textops:
                    for function in objects:
                        func_name = function['name']
                        func_code = function['code']
                        object_name = function.get('object', None)
                        matched_class = None
                        insert_pos = None
                        end_pos = None
                        cursor_pos = None
                        for x, line in enumerate(top_panel_copy):
                            if object_name and line.strip().startswith(f"class {object_name}"):
                                matched_class = object_name
                            if matched_class == object_name and func_name in line and re.match(r'^\s*def\b', line):
                                indent_level = len(line) - len(line.lstrip())
                                indent = ' ' * indent_level
                                insert_pos = x
                                for y, end_line in enumerate(top_panel_copy[x+1:], start=x+1):
                                    if re.match(r'^\s*(def|class)\b', end_line):
                                        end_pos = y
                                        break
                                if end_pos is None:
                                    end_pos = len(top_panel_copy)
                                org_code =  [l for l in top_panel_copy[insert_pos:end_pos]]
                                refactored_code = []
                                refactored_code = [f"{indent}''' [{self.viewpoints.get_current_name()} --Refactor][{object_name}::{func_name}][Rev:{self.revision_manager.rev_num} Sub:{self.revision_manager.subrev_num+1}][Type: Markup]\n"]
                                for l in func_code.split('\n'):
                                    if 'def' in l:
                                        refactored_code += [indent + l]
                                    else:
                                        refactored_code += [l]
                                refactored_code += [f"{indent}'''"]
                                refactored_code += [f"\n"]
                                if cursor_pos == None:
                                    cursor_pos = insert_pos
                                else:
                                    if insert_pos < cursor_pos:
                                        cursor_pos = insert_pos
                                top_panel_copy = (
                                    top_panel_copy[:insert_pos] +
                                    org_code + refactored_code +
                                    top_panel_copy[end_pos:]
                                )
                                break
                        if insert_pos is None and not object_name:
                            indent = ' ' * 4
                            new_code = []
                            new_code += [indent + l for l in func_code.split('\n')]
                            top_panel_copy.extend([f"\n'' ' [{self.viewpoints.get_current_name()}[--new]\n'' '", new_code, ""])
                    top_panel_copy.append(f"'''")
                    top_panel_copy.append(f"[{self.viewpoints.get_current_name()}][--Concatenate][Rev: {self.revision_manager.rev_num}][Sub_rev: {self.revision_manager.subrev_num+1}]")
                    top_panel_copy.extend(response_text)
                    top_panel_copy.append(f"'''")
                    top_panel_copy.append(f"")
                    self.panels[0]["line_num"] = cursor_pos
                elif 'Concatenate' in textops:
                    top_panel_copy.append(f"'''")
                    top_panel_copy.append(f"[{self.viewpoints.get_current_name()}][--Concatenate][Rev: {self.revision_manager.rev_num}][Sub_rev: {self.revision_manager.subrev_num+1}]")
                    top_panel_copy.extend(response_text)
                    top_panel_copy.append(f"'''")
                    top_panel_copy.append(f"")
                return top_panel_copy
    def refactor_cpp_edit_panel(self, response_text, objects, textops):
        top_panel_copy = self.panels[0]["text"][:]
        cursor_pos = 0
        if 'Replace' in textops:
            top_panel_copy = ["/*\n"]
            for line in response_text:
                if "```" in line:
                    top_panel_copy.append("/*")
                top_panel_copy.append(line)
                if "```cpp" in line:
                    top_panel_copy.append("*/")
            top_panel_copy.append("*/")
        if 'Refactor' in textops or 'Deprecate' in textops:
            for function in objects:
                func_name = function['name']
                func_code = function['code']
                object_name = function.get('object', None)
                matched_class = None
                insert_pos = None
                end_pos = None
                for x, line in enumerate(top_panel_copy):
                    if object_name and isinstance(line, str) and line.strip().startswith(f"class {object_name}"):
                        matched_class = object_name
                    if matched_class == object_name and func_name in line and re.match(r'^\s*\w+\s+\w+\(', line):
                        indent_level = len(line) - len(line.lstrip())
                        indent = ' ' * indent_level
                        insert_pos = x
                        for y, end_line in enumerate(top_panel_copy[x+1:], start=x+1):
                            if isinstance(end_line, str) and (re.match(r'^\s*\w+\s+\w+\(', end_line) or re.match(r'^\s*class\b', end_line)):
                                end_pos = y
                                break
                        if end_pos is None:
                            end_pos = len(top_panel_copy)
                        commented_code = [f"{indent}/* [{self.viewpoints.get_current_name()} --Deprecate][{object_name}::{func_name}][Rev:{self.revision_manager.rev_num} Sub:{self.revision_manager.subrev_num+1}][Type: Deprecate]"] + [l for l in top_panel_copy[insert_pos:end_pos]] + [f"{indent}*/"]
                        refactored_code = []
                        if 'Deprecate' in textops:
                            refactored_code = [f"{indent}// [{self.viewpoints.get_current_name()} --Refactor][{object_name}::{func_name}][Rev:{self.revision_manager.rev_num} Sub:{self.revision_manager.subrev_num+1}][Type: Deprecate]\n"]
                        for l in func_code.split('\n'):
                            refactored_code += [indent + l]
                        if 'Deprecate' in textops:
                            top_panel_copy = (
                                top_panel_copy[:insert_pos] +
                                commented_code + refactored_code +
                                top_panel_copy[end_pos:]
                            )
                        if 'Refactor' in textops:
                            top_panel_copy = (
                                top_panel_copy[:insert_pos] +
                                refactored_code +
                                top_panel_copy[end_pos:]
                            )
                        break
                if insert_pos is None and not object_name:
                    indent = ' ' * 4
                    new_code = []
                    new_code += [indent + l for l in func_code.split('\n')]
                    top_panel_copy.extend([f"\n/* [{self.viewpoints.get_current_name()}[--new]\n*/", new_code, ""])
        if 'Markup' in textops:
            for function in objects:
                func_name = function['name']
                func_code = function['code']
                object_name = function.get('object', None)
                matched_class = None
                insert_pos = None
                end_pos = None
                cursor_pos = None
                for x, line in enumerate(top_panel_copy):
                    if object_name and isinstance(line, str) and line.strip().startswith(f"class {object_name}"):
                        matched_class = object_name
                    if matched_class == object_name and func_name in line and re.match(r'^\s*\w+\s+\w+\(', line):
                        indent_level = len(line) - len(line.lstrip())
                        indent = ' ' * indent_level
                        insert_pos = x
                        for y, end_line in enumerate(top_panel_copy[x+1:], start=x+1):
                            if isinstance(end_line, str) and (re.match(r'^\s*\w+\s+\w+\(', end_line) or re.match(r'^\s*class\b', end_line)):
                                end_pos = y
                                break
                        if end_pos is None:
                            end_pos = len(top_panel_copy)
                        org_code =  [l for l in top_panel_copy[insert_pos:end_pos]]
                        refactored_code = []
                        refactored_code = [f"{indent}/* [{self.viewpoints.get_current_name()} --Refactor][{object_name}::{func_name}][Rev:{self.revision_manager.rev_num} Sub:{self.revision_manager.subrev_num+1}][Type: Markup]\n"]
                        for l in func_code.split('\n'):
                            refactored_code += [indent + l]
                        refactored_code += [f"{indent}*/"]
                        refactored_code += [f"\n"]
                        if cursor_pos is None:
                            cursor_pos = insert_pos
                        else:
                            if insert_pos < cursor_pos:
                                cursor_pos = insert_pos
                        top_panel_copy = (
                            top_panel_copy[:insert_pos] +
                            org_code + refactored_code +
                            top_panel_copy[end_pos:]
                        )
                        break
                if insert_pos is None and not object_name:
                    indent = ' ' * 4
                    new_code = []
                    new_code += [indent + l for l in func_code.split('\n')]
                    top_panel_copy.extend([f"\n/* [{self.viewpoints.get_current_name()}[--new]\n*/", new_code, ""])
            top_panel_copy.append(f"/*")
            top_panel_copy.append(f"[{self.viewpoints.get_current_name()}][--Concatenate][Rev: {self.revision_manager.rev_num}][Sub_rev: {self.revision_manager.subrev_num+1}]")
            top_panel_copy.extend(response_text)
            top_panel_copy.append(f"*/")
            top_panel_copy.append(f"")
            self.panels[0]["line_num"] = cursor_pos
        elif 'Concatenate' in textops:
            top_panel_copy.append(f"/*")
            top_panel_copy.append(f"[{self.viewpoints.get_current_name()}][--Concatenate][Rev: {self.revision_manager.rev_num}][Sub_rev: {self.revision_manager.subrev_num+1}]")
            top_panel_copy.extend(response_text)
            top_panel_copy.append(f"*/")
            top_panel_copy.append(f"")
        return top_panel_copy
    def write_file(self):
        self.status = self.revision_manager.write_file(self.viewpoints, self.panels[0]["text"], self.panels[1]["text"])
    def read_file(self, filename):
        self.status, self.panels[0]["text"] = self.revision_manager.read_file()
    def delete_current_line(self):
        self.status = 'delln'
        current_line = self.panels[self.context_panel]["line_num"]
        self.yank_mode_active = 'del'
        if len(self.panels[self.context_panel]["text"]) > 1:
            line = self.panels[self.context_panel]["text"].pop(current_line)
            self.clipboard = [line]
            if current_line >= len(self.panels[self.context_panel]["text"]):
                self.panels[self.context_panel]["line_num"] -= 1
            self.panels[self.context_panel]["col_num"] = 0
        else:
            line = self.panels[self.context_panel]["text"][0]
            self.clipboard = [line]
            self.panels[self.context_panel]["text"] = [""]
            self.panels[self.context_panel]["line_num"] = 0
            self.panels[self.context_panel]["col_num"] = 0
        self.adjust_panel_offset()
    def handle_ctrl_x(self):
        current_line = self.panels[self.context_panel]["line_num"]
        if current_line in self.yanked_lines:
            self.yanked_lines.remove(current_line)
            self.status = 'unmrk'
        else:
            if self.yank_mode_active == 'off' or self.yank_mode_active == 'del':
                self.yanked_lines.clear()
                self.yank_mode_active = 'yank'
                self.status = 'xtrac'
            elif self.yank_mode_active == 'yank':
                self.status = 'mark'
        self.yanked_lines.add(current_line)
        self.mode = 'line'
        self.handle_down_arrow()
    def handle_ctrl_y(self):
        if self.yank_mode_active == 'yank' and self.yanked_lines:
            self.clipboard = [self.panels[self.context_panel]["text"][line] for line in sorted(self.yanked_lines)]
            self.yanked_lines.clear()
            self.yank_mode_active = 'off'
            self.mode = 'line'
            self.status = 'yankd'
    def handle_ctrl_p(self):
        if self.clipboard:
            buffer = list(self.panels[self.context_panel]["text"])
            current_line = self.panels[self.context_panel]["text"][self.panels[self.context_panel]["line_num"]]
            for line in self.clipboard:
                self.panels[self.context_panel]["text"].insert(self.panels[self.context_panel]["line_num"], line)
                self.panels[self.context_panel]["line_num"] += 1
            self.panels[self.context_panel]["col_num"] = len(current_line)
            self.clipboard = []
            self.clipboard = buffer
            self.mode = 'line'
            self.status = 'paste'
            self.adjust_panel_offset()
    def handle_ctrl_k(self):
        if self.context_panel == 0 and self.mode == 'line':
            self.panels[0]["line_num"] += self.top_panel_size
            if self.panels[0]["line_num"] >= len(self.panels[0]["text"]):
                self.panels[0]["line_num"] = len(self.panels[0]["text"]) - 1
            if self.panels[0]["col_num"] > len(self.panels[0]["text"][self.panels[0]["line_num"]]):
                self.panels[0]["col_num"] = len(self.panels[0]["text"][self.panels[0]["line_num"]])
            self.adjust_panel_offset()
        else:
            self.insert_char(ord('\\'))
    def handle_ctrl_v(self):
        self.context.reset(self.viewpoints)
        self.context.get_cogtext_by_name(self.viewpoints.next_viewpoint())
        self.adjust_panel_offset()
        self.display()
    def search_text(self):
        bottom_panel = self.panels[1]["text"]
        current_line_number = self.panels[1]["line_num"]
        search_term = bottom_panel[current_line_number].strip()
        if not search_term:
            self.status = 'no tm'
            return
        self.search_results.clear()
        top_panel = self.panels[0]["text"]
        for i, line in enumerate(top_panel):
            start_idx = 0
            while start_idx < len(line):
                start_idx = line.find(search_term, start_idx)
                if start_idx == -1:
                    break
                self.search_results.append((i, start_idx))
                start_idx += len(search_term)
        if self.search_results:
            self.current_search_result = 0
            self.highlight_search_result()
            self.status = f"fnd{len(self.search_results):02}"
            self.context_panel = 0
        else:
            self.status = 'not f'
    def search_offset(self):
        for i in range(2):
            panel_size = self.top_panel_size if i == 0 else self.bottom_panel_size
            line_num = self.panels[i].get("line_num", 0)
            if line_num is None:
                line_num = 0  # Default to 0 if line_num is None
            middle_offset = max(0, int(line_num) - panel_size // 2)
            self.panel_offsets[i] = min(middle_offset, len(self.panels[i]["text"]) - panel_size)
            self.panel_offsets[i] = max(0, self.panel_offsets[i])
    def highlight_search_result(self):
        if not self.search_results:
            return
        line_num, col_num = self.search_results[self.current_search_result]
        self.panels[0]["line_num"] = line_num
        self.panels[0]["col_num"] = col_num
        self.search_offset()
    def next_search_result(self):
        if self.search_results:
            self.current_search_result = (self.current_search_result + 1) % len(self.search_results)
            self.highlight_search_result()
    def prev_search_result(self):
        if self.search_results:
            self.current_search_result = (self.current_search_result - 1) % len(self.search_results)
            self.highlight_search_result()
    def insert_as_current_line(self, text):
        self.panels[self.context_panel]["text"][self.panels[self.context_panel]["line_num"]] = text
        self.panels[self.context_panel]["col_num"] = len(text)
        self.adjust_panel_offset()
    def insert_lines_at_current_line(self, text):
        lines = text.split('\n')
        current_line_index = self.panels[self.context_panel]["line_num"]
        current_column_index = self.panels[self.context_panel]["col_num"]
        first_line = self.panels[self.context_panel]["text"][current_line_index] if current_line_index < len(self.panels[self.context_panel]["text"]) else ""
        new_first_line = first_line[:current_column_index] + lines[0]
        if current_column_index < len(first_line):
            new_first_line += first_line[current_column_index:]
        if current_line_index < len(self.panels[self.context_panel]["text"]):
            self.panels[self.context_panel]["text"][current_line_index] = new_first_line
        else:
            self.panels[self.context_panel]["text"].append(new_first_line)
        for line in reversed(lines[1:]):
            self.panels[self.context_panel]["text"].insert(current_line_index + 1, line)
            current_line_index += 1
        self.panels[self.context_panel]["line_num"] += len(lines) - 1
        self.panels[self.context_panel]["col_num"] = len(lines[-1])
        if self.panels[self.context_panel]["line_num"] >= len(self.panels[self.context_panel]["text"]):
            self.panels[self.context_panel]["text"].append("")
        self.panels[self.context_panel]["line_num"] += 1
        self.adjust_panel_offset()
    def handle_ctrl_n(self):
        if self.search_results:
            self.next_search_result()
        else:
            self.panels[self.context_panel]["line_num"] += curses.LINES - 1
            if self.panels[self.context_panel]["line_num"] >= len(self.panels[self.context_panel]["text"]):
                self.panels[self.context_panel]["line_num"] = len(self.panels[self.context_panel]["text"]) - 1
            self.adjust_panel_offset()
    def handle_del_key(self):
        line = self.panels[self.context_panel]["text"][self.panels[self.context_panel]["line_num"]]
        if self.panels[self.context_panel]["col_num"] < len(line):
            self.panels[self.context_panel]["text"][self.panels[self.context_panel]["line_num"]] = line[:self.panels[self.context_panel]["col_num"]] + line[self.panels[self.context_panel]["col_num"] + 1:]
        elif self.panels[self.context_panel]["col_num"] == len(line) and self.panels[self.context_panel]["line_num"] < len(self.panels[self.context_panel]["text"]) - 1:
            next_line = self.panels[self.context_panel]["text"].pop(self.panels[self.context_panel]["line_num"] + 1)
            self.panels[self.context_panel]["text"][self.panels[self.context_panel]["line_num"]] += next_line
        self.adjust_panel_offset()
    def handle_home_key(self):
        self.panels[self.context_panel]["col_num"] = 0
        self.mode = 'edit'
    def handle_end_key(self):
        self.panels[self.context_panel]["col_num"] = len(self.panels[self.context_panel]["text"][self.panels[self.context_panel]["line_num"]])
        self.mode = 'edit'
    def handle_ctrl_a(self):
        self.context_panel = 1 - self.context_panel
        if self.context_panel == 1:
            self.mode = 'commd'
        else:
            self.mode = 'edit'
    def handle_ctrl_e(self):
        self.status = "execu"
        self.display()
        self.write_file()
        shell_command = ""
        shellcm = self.viewpoints.get_shell()
        if shellcm is not None:
            shell_command += shellcm.replace('$$sessionname', self.revision_manager.original_filename)
            try:
                result = subprocess.run(
                    ['bash', '-c', shell_command],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                stdout_lines = result.stdout.split('\n')
                stderr_lines = result.stderr.split('\n')
                self.panels[1]['text'].append(f"Shell: {shell_command}")
                self.panels[1]['text'].append("stdout:")
                self.panels[1]['text'].extend(stdout_lines)
                self.panels[1]['text'].append("stderr:")
                self.panels[1]['text'].extend(stderr_lines)
            except subprocess.CalledProcessError as e:
                self.panels[1]['text'].append(f"Shell: {shell_command}")
                self.panels[1]['text'].append(f"Called Process Error:\n{str(e)}")
            except Exception as e:
                self.panels[1]['text'].append(f"Shell: {shell_command}")
                self.panels[1]['text'].append(f"Error:\n{str(e)}")
            with open(f"e.debug", "w") as f:
                f.write(f"\nshell: {shell_command}\n")
        else:
            try:
                result = subprocess.run(
                    ['python', self.revision_manager.original_filename],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                stdout_lines = result.stdout.split('\n')
                stderr_lines = result.stderr.split('\n')
                self.panels[1]['text'].append("Execution Results:")
                self.panels[1]['text'].append("stdout:")
                self.panels[1]['text'].extend(stdout_lines)
                self.panels[1]['text'].append("stderr:")
                self.panels[1]['text'].extend(stderr_lines)
            except subprocess.CalledProcessError as e:
                self.panels[1]['text'].append(f"Called Process Error:\n{str(e)}")
            except Exception as e:
                self.panels[1]['text'].append(f"Error:\n{str(e)}")
        self.adjust_panel_offset()
        self.display()
    def handle_ctrl_h(self):
        #Below is for debug testing.
        self.status = "Ctrl-h"
    def handle_ctrl_u(self):
        #Below is for debug testing.
        pmys = self.revision_manager.update_pmy_summary(self.viewpoints)
        self.status = "Ctrl-u"
        self.display()
    def handle_ctrl_m(self):
        self.mode = "not captured ctrl-m"
    def handle_ctrl_q(self):
        self.mode = "not captured ctrl-q"
    def handle_ctrl_s(self):
        self.mode = "not captured ctrl-s"
    def handle_ctrl_t(self):
            self.revision_manager.subrev_being_viewed += 1
            sub_text = self.revision_manager.get_subrevision_text(self.revision_manager.subrev_being_viewed)
            if not sub_text:
                self.revision_manager.subrev_being_viewed = 0
                sub_text = self.revision_manager.get_subrevision_text(self.revision_manager.subrev_being_viewed)
            if sub_text:
                self.panels[0]["text"] = sub_text
                if self.panels[0]["line_num"] >= len(self.panels[0]["text"]):
                    self.panels[0]["line_num"] = len(self.panels[0]["text"]) - 1
                if self.panels[0]["line_num"] < 0:
                    self.panels[0]["line_num"] = 0
                if self.panels[0]["col_num"] > len(self.panels[0]["text"][self.panels[0]["line_num"]]):
                    self.panels[0]["col_num"] = len(self.panels[0]["text"][self.panels[0]["line_num"]])
                if self.panels[0]["col_num"] < 0:
                    self.panels[0]["col_num"] = 0
                self.adjust_panel_offset()
            self.status = "subrv"
            self.display()
    def handle_ctrl_g(self):
            self.show_left_column = not self.show_left_column
            self.status = "bell"
            self.display()
    def load_viewpoints(self):
        for root, dirs, files in os.walk('QK/Viewpoints'):
            for filename in files:
                if filename.endswith('.Viewpoint'):
                    file_path = os.path.join(root, filename)
                    with open(file_path, 'r') as f:
                        viewpoint_data = json.load(f)
                    self.viewpoints.load_viewpoint(viewpoint_data)
        for root, dirs, files in os.walk('.'):
            if 'Viewpoints' in dirs:
                viewpoints_path = os.path.join(root, 'Viewpoints')
                for vp_root, vp_dirs, vp_files in os.walk(viewpoints_path):
                    for vp_filename in vp_files:
                        if vp_filename.endswith('.Viewpoint'):
                            vp_file_path = os.path.join(vp_root, vp_filename)
                            with open(vp_file_path, 'r') as f:
                                viewpoint_data = json.load(f)
                            self.viewpoints.load_viewpoint(viewpoint_data)
    def handle_sigint(self, sig, frame):
        self.stdscr.addstr(38, 0, f'Ctrl-C, are you sure you want to exit? (Q/n/W), save your qk edit [{self.revision_manager.original_filename}], beforehand.', curses.A_REVERSE | curses.A_BOLD)
        self.stdscr.refresh()
        while True:
            ch = self.stdscr.getch()
            if ch == ord('Q'):
                raise SystemExit
            elif ch == ord('n') or ch == ord('N'):
                self.display()
                return
            elif ch == ord('W'):
                self.write_file()
                raise SystemExit
    def handle_sigtstp(self, sig, frame):
        self.status = 'pause'
        self.context_panel = 1
        self.display()
    def run(self):
        while True:
            self.display()
            ch = self.stdscr.getch()
            if ch in self.keymap:
                self.keymap[ch]()
            else:
                if self.panels[self.context_panel]["line_num"] >= len(self.panels[self.context_panel]["text"]):
                    self.panels[self.context_panel]["text"].append('')
                self.insert_char(ch)
    def show_splash_screen(self):
        self.stdscr.clear()
        self.status = 'splsh'
        splash_text = [
            "",
            "Welcome to the AIQuickKeyEditor!",
            "    qk for short ;)",
            "",
            "Control Characters:",
            "Ctrl-A: Switch between editor panel and AI command prompt panel.",
            "Ctrl-V: Switch AI Viewpoint, E.g. Spelling, Grammar, Python Coder.",
            "Ctrl-W: Write the editor panel to a file.",
            "Ctrl-R: Read the file to edit.",
            "Backslash key (\\): Quick Key AI Viewpoint Query.  Just key the backslash.",
            "Backspace key (<-): Toggle between the AI Viewpoint and the original, for quick comparison.",
            "Ctrl-D: Delete a line.",
            "Ctrl-X: Extract and mark lines (repeat Ctrl-X).",
            "Ctrl-Y: Yank (copy) the marked lines.",
            "Ctrl-P: Paste the yanked lines.",
            "Ctrl-K: If you need a backslash.",
            "Ctrl-T: Toggle Text through subrevisions.",
            "Use the arrow keys to navigate.",
            "",
            "Try:",
            "Type: 'Write a script that prints the Fibonacci series up to 89 inclusive.'",
            "Crtl-V to change viewpoint to Spelling.",
            "Depress the \\ key to fix spelling, inline, in the AI command prompt panel,",
            "Crtl-V to change viewpoint to Python Coder.",
            "Press the \\ key to send your request to AI.",
            "Crtl-E to execute your code.",
            "",
            "Enjoy qk, your AI-Assisted text and code writing experience!"
        ]
        splash_text_width = max(len(line) for line in splash_text) + 1
        splash_text_height = len(splash_text)
        screen_height, screen_width = self.stdscr.getmaxyx()
        if screen_height < 26:
            lines_to_show = [splash_text[0], splash_text[1], splash_text[-1]]
        else:
            lines_to_show = splash_text
        for y, line in enumerate(lines_to_show):
            if y >= len(lines_to_show):
                break
            x = ((screen_width - splash_text_width) // 2) - 2
            self.stdscr.addstr(y, x, line)
            self.stdscr.addstr(y, 0, f"{y + 1:03}<{self.mode:5}>", curses.A_REVERSE)
        self.mode = ''
        self.stdscr.refresh()
        self.stdscr.getch()
def main(stdscr):
    editor = QKEditor(stdscr)
    editor.run()

if __name__ == "__main__":
    curses.wrapper(main)



