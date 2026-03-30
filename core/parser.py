import re

class FlowParser:
    def __init__(self, raw_code):
        self.raw_code = raw_code
        self.nodes = {}  # ID -> {'label': str, 'bracket': char}
        self.edges = []  # List of {'from': str, 'to': str, 'label': str}

    def parse(self):
        self.nodes = {}
        self.edges = []
        
        # Extract between ErStart and ErStop
        content_match = re.search(r'ErStart\s*(.*?)\s*ErStop', self.raw_code, re.DOTALL | re.IGNORECASE)
        if not content_match:
            return {'nodes': [], 'edges': []}
            
        lines = content_match.group(1).split('\n')
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # --- Type 1: ID-"Label"-ID{ShapeLabel} ---
            # e.g. 2-"yes"-3{ok}
            full_rel = re.match(r'^(\w+)-"([^"]+)"-(\w+)([\[\{\(])([^\]\}\)]+)([\]\}\)])\s*$', line)
            if full_rel:
                s_id, edge_lbl, t_id, bracket, t_lbl = full_rel.groups()[:5]
                self._add_node(s_id)
                self._add_node(t_id, t_lbl, bracket)
                self.edges.append({'from': s_id, 'to': t_id, 'label': edge_lbl})
                continue

            # --- Type 2: ID-ID[ShapeLabel] ---
            # e.g. 1-2[content]
            shorthand_rel = re.match(r'^(\w+)-(\w+)([\[\{\(])([^\]\}\)]+)([\]\}\)])\s*$', line)
            if shorthand_rel:
                s_id, t_id, bracket, t_lbl = shorthand_rel.groups()[:4]
                self._add_node(s_id)
                self._add_node(t_id, t_lbl, bracket)
                self.edges.append({'from': s_id, 'to': t_id, 'label': ""})
                continue

            # --- Type 3: ID([ShapeLabel]) --- (Standalone Definition)
            # e.g. 1([start])
            standalone_node = re.match(r'^(\w+)([\[\{\(])([^\]\}\)]+)([\]\}\)])\s*$', line)
            if standalone_node:
                n_id, bracket, n_lbl = standalone_node.groups()[:3]
                self._add_node(n_id, n_lbl, bracket)
                continue

            # --- Type 4: ID-"Label"-ID ---
            # e.g. 3-"no"-2
            labeled_link = re.match(r'^(\w+)-"([^"]+)"-(\w+)\s*$', line)
            if labeled_link:
                s_id, edge_lbl, t_id = labeled_link.groups()
                self._add_node(s_id)
                self._add_node(t_id)
                self.edges.append({'from': s_id, 'to': t_id, 'label': edge_lbl})
                continue

            # --- Type 5: ID-ID (Simple arrow) ---
            # e.g. 1-2
            simple_link = re.match(r'^(\w+)-(\w+)\s*$', line)
            if simple_link:
                s_id, t_id = simple_link.groups()
                self._add_node(s_id)
                self._add_node(t_id)
                self.edges.append({'from': s_id, 'to': t_id, 'label': ""})
                continue

        return {
            'nodes': list(self.nodes.values()),
            'edges': self.edges
        }

    def _add_node(self, node_id, label=None, bracket='['):
        if node_id not in self.nodes:
            # Default to box if no shape specified yet
            self.nodes[node_id] = {'id': node_id, 'label': label or node_id, 'bracket': bracket}
        elif label:
            # Update label and shape if explicitly provided later
            self.nodes[node_id]['label'] = label
            self.nodes[node_id]['bracket'] = bracket

    def to_mermaid(self):
        data = self.parse()
        if not data['nodes'] and not data['edges']:
            return "graph TD\n    Init[Use ErStart and ErStop]"

        lines = ["graph TD"]
        
        # Styles for oval (start/stop)
        lines.append("    classDef oval fill:#f9f,stroke:#333; ")
        
        for node in data['nodes']:
            b_open = node['bracket']
            b_close = ']' if b_open == '[' else ('}' if b_open == '{' else ')')
            
            # Mermaid Oval syntax: ID([label])
            if b_open == '(': 
                b_open, b_close = '([', '])'
            
            lines.append(f"    {node['id']}{b_open}\"{node['label']}\"{b_close}")

        for edge in data['edges']:
            label_part = f"|{edge['label']}|" if edge['label'] else ""
            lines.append(f"    {edge['from']} -->{label_part} {edge['to']}")

        return "\n".join(lines)
