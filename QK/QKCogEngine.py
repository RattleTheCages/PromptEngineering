#
#           QKCogEngine     -- An awesome AI Cognitive Engine
#
# The QKCogEngine is here!  To handle AI cognitive tasks.
# With QKCogEngine ;), you don't just get results, you engage in an intelligent dialogue.
# Ask for thoughtful responses, detailed analyses, or creative outputs in the most intuitive manner.
# Select the viewpoint that suits your cognitive needs, from simple summaries to in-depth explorations.
# This work is copyright, Daniel Huffman, pen name Rattle. All rights reserved.

import re
import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("CUSTOM_ENV_NAME"))

class QKCogEngine:
    def __init__(self, viewpoints):
        self.viewpoints = viewpoints
        self.cogessages = []
        self.usermsg = []
    def reset(self, viewpoint):
        self.cogessages = []
        self.usermsg = []
        for attribute in viewpoint.get_attributes():
            self.add_cogtext("system", attribute)
    def reset_viewpoint(self, viewpoints, view):
        self.cogessages = []
        self.usermsg = []
        for attribute in viewpoints.get_attributes_by_name(view):
            self.add_cogtext("system", attribute)
    def add_cogtext(self, role, content):
        self.cogessages.append({"role": role, "content": content})
    def get_cogtext(self):
        context = [{"role": message["role"], "content": message["content"]} for message in self.cogessages]
        context += [{"role": "user", "content": umsg} for umsg in self.usermsg]
        return context
    def get_cogtext_by_name(self, name):
        attributes = self.viewpoints.get_attributes_by_name(name)
        context = [{"role": "system", "content": attribute} for attribute in attributes]
        context += [{"role": "user", "content": umsg} for umsg in self.usermsg]
        return context
    def add_usermsg(self, msg):
        self.usermsg.append(msg)
    def ai_query(self, viewpoints):
        reform = client.chat.completions.create(
            model = viewpoints.get_model(),
            max_tokens = viewpoints.get_maxtokens(),
            temperature = viewpoints.get_temperature(),
            messages = self.get_cogtext()
        )
        self.add_cogtext("assistant", reform.choices[0].message.content)
        return reform
    def save_cogtext(self):
        with open("cogtext_debug.json", 'w') as cogf:
            json.dump({
                "model": self.viewpoints.get_model(),
                "max_tokens": self.viewpoints.get_maxtokens(),
                "temperature": self.viewpoints.get_temperature(),
                "messages": self.get_cogtext()
            }, cogf)
    def extract_objects(self, content):
        obj_pattern = re.compile(r'class\s+(\w+)|def\s+(\w+)\s*\((.*?)\):')
        matches = obj_pattern.finditer(content)
        objects = []
        current_class = None
        for match in matches:
            if match.group(1):
                current_class = match.group(1)
            else:
                obj_name = match.group(2)
                start_pos = match.start()
                lines = content[start_pos:].splitlines()
                code_block = []
                indent_level = None
                for line in lines:
                    if '```' in line:
                        break
                    stripped_line = line.lstrip()
                    if stripped_line.startswith('def') and code_block:
                        break
                    if stripped_line.startswith('class') and code_block:
                        break
                    if stripped_line and indent_level is None:
                        indent_level = len(line) - len(stripped_line)
                    if indent_level is not None:
                        if len(line) - len(stripped_line) < indent_level and stripped_line:
                            break
                        code_block.append(line)
                objects.append({
                    'name': obj_name,
                    'object': current_class,
                    'code': '\n'.join(code_block)
                })
        with open(f"refacobjs.debug", "a") as f:
            for obj in objects:
                f.write(f"Object: {obj['object']}\n")
                f.write(f"Function: {obj['name']}\n")
                f.write(f"Code:\n{obj['code']}\n")
        return objects

class Viewpoints:
        def __init__(self):

                self.viewpoints = {
                    'Spelling': {
                        "arrange": 1000,
                        "name": "Spelling",
                        "attributes": [
                            "Your only task is to correct misspelled words.",
                            "Take each sentence and output a corresponding corrected sentence.",
                            "Answer only using the correctly spelled words, do not change punctuation or sentence structure.",
                            "Do not change the placement of the new lines.",
                            "The user wants the answer strictly formatted as the sample sentence."
                        ],
                        "model": "gpt-3.5-turbo",
                        "max_tokens": 298,
                        "temperature": 0.68,
                        "textops": ["Inline"],
                        "role": ["Editor"]
                    },
                    'Freestyle': {
                        'arrange': 6000,
                        'name': 'Freestyle',
                        'attributes': [],
                        'model': 'gpt-4o',
                        'max_tokens': 4096,
                        'temperature': 0.88,
                        'textops': ['Concatenate'],
                        'role' : ['Editor']
                    },
                    'Pmt_Summary': {
                        'arrange': 4202,
                        'name': 'Pmt Summary',
                        'attributes': [
                            "Provide a short summary the length of about 8 words or so.",
                            "Do not perform the work, your task is to summarize the work.",
                            "Do not say you are writing a summary, just write a summary."
                        ],
                        'model': 'gpt-4o-mini',
                        'max_tokens': 198,
                        'temperature': 0.88,
                        'textops': ['Replace'],
                        'role' : ['Editor', 'System', 'Hidden']
                    }
                }
                self.names = list(self.viewpoints.keys())
                self.current_index = 0
        def test_textop(self, textop_name):
            return textop_name in self.viewpoints[self.get_current_name()]['textops']
        def get_current_name(self):
            return self.names[self.current_index]
        def get_attributes(self):
            return self.viewpoints[self.get_current_name()]['attributes']
        def get_attributes_by_name(self, name):
            return self.viewpoints[name]['attributes']
        def get_model(self):
            return self.viewpoints[self.get_current_name()]['model']
        def get_maxtokens(self):
            return self.viewpoints[self.get_current_name()]['max_tokens']
        def get_textops(self):
            return self.viewpoints[self.get_current_name()]['textops']
        def get_role(self):
            return self.viewpoints[self.get_current_name()]['role']
        def get_temperature(self):
            return self.viewpoints[self.get_current_name()]['temperature']
        def next_viewpoint(self):
                starting_index = self.current_index
                while True:
                    self.current_index = (self.current_index + 1) % len(self.names)
                    if 'Hidden' not in self.viewpoints[self.names[self.current_index]]['role']:
                        break
                    if self.current_index == starting_index:
                        break
                return self.get_current_name()
        def get_attributes_by_name(self, name):
            return self.viewpoints.get(name, {}).get('attributes', [])
        def load_viewpoint(self, viewpoint):
            name = viewpoint['name']
            if name and name not in self.viewpoints:
                self.viewpoints[name] = viewpoint
                self.names.append(name)
            self.names.sort(key=lambda vp: self.viewpoints[vp]['arrange'])

