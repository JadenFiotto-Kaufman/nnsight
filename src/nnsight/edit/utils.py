from typing import List
import torch
import re
from rich.console import Console

def print_gm(module):
    module.clear_hooks()
    fake_inputs = module._fake_inputs[0][0][0]

    def custom_backend(gm: torch.fx.GraphModule, _: List[torch.Tensor]):
        colors = {
            "call_function": "dodger_blue2",
            "call_method": "green",
            "call_module": "red",
            "placeholder": "yellow",
            "output": "purple",
            "get_attr": "orange"
        }

        replacements = [
            ("return" if node.op == "output" else node.name, colors[node.op])
            for node in gm.graph.nodes
        ]

        filtered_lines = [
            line for line in str(gm).replace("# To see more debug info, please use `graph_module.print_readable()`", "").splitlines()
            if line.strip()
        ]

        console = Console(highlight=False)

        # Process lines for coloring after the 'def forward' line
        colored_lines = []
        body_started = False
        replacement_index = 0
        for line in filtered_lines:
            if "def forward" in line:
                body_started = True
                colored += line + "\n"
                continue  
            if body_started:
                name, color = replacements[replacement_index]
                # Replace name with colored name directly
                colored_line = re.sub(rf'\b{name}\b', f"[{color}]{name}[/{color}]", line)
                replacement_index += 1
            else:
                colored_line = line
            colored_lines.append(colored_line)

        # Print all lines at once
        console.print("\n".join(colored_lines))

        return gm.forward

    # Reset and compile with the custom backend, then set hooks
    torch._dynamo.reset()
    opt_model = torch.compile(module._module, backend=custom_backend, dynamic=True)
    _ = opt_model(fake_inputs)  # Execute optimized model with fake inputs
    module.set_hooks()
