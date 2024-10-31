#!/usr/bin/env python3

import sys
import json

from dndtex import Util

def clean(input):
    if input is None: 
        return ''
    input = Util.remove_tag(input)
    return input.replace("&", "\\&").replace("&quot;", "\"").replace("_", "\\_").replace("%","\\%").replace("#","\\#")


def main():
    filename = sys.argv[1]

    fh = open(filename, 'r', encoding="utf8")
    data = json.load(fh)
    fh.close()    
    print(r"""
\documentclass[10pt,a4paper,twoside,bg=print,twocolumn,openany,nodeprecatedcode]{dndbook}
\usepackage[utf8]{inputenc}
\usepackage{tabulary}
\usepackage[normalem]{ulem}
\usepackage{color,soul}
\usepackage{tocloft}
\usepackage{multicol} % To handle the column switching
\usepackage[toc]{multitoc}
\usepackage[hidelinks]{hyperref}
\raggedbottom
\extrafloats{2000}
\cftsetindents{section}{0em}{0em}
\cftsetindents{subsection}{0em}{0em}
\cftsetindents{subsubsection}{0.2em}{0em}
\setcounter{tocdepth}{3}
\renewcommand*{\multicolumntoc}{2}
\setlist[description]{nolistsep,listparindent=3pt,topsep=6pt}
\date{}

\begin{document}
\tableofcontents
\markboth{RANDOM TABLES}{RANDOM TABLES}
          """)
    for table in data['table']:
        name = table['name']
        # print(f"{{\n  \\par \\vspace {{9pt plus 3pt minus 3pt}} \\noindent\n  \\DndFontTableTitle{{{name}}} \\nopagebreak\n}}")        
        print(f"\\chapter*{{{name}}}")
        # print(r"\addcontentsline{toc}{subsubsection}{" + name + "}")

        col_labels = table['colLabels']
        print("\\begin{dndlongtable}[c p{0.85\\linewidth}]")
        print(" & ".join(map(lambda x: f"\\textbf{{{x}}}", col_labels)) + " \\\\")
        for row in table['rows']:
           print(" & ".join(map(clean, row)) + " \\\\")
          
        print("\\end{dndlongtable}\n\\newpage")
        
    print(r"\end{document}")
#   \par \vspace { 9pt plus 3pt minus 3pt } \noindent
#   \DndFontTableTitle{Infinite Staircase Doors} \nopagebreak
# }
# \begin{dndlongtable}[c p{0.33\linewidth} p{0.33\linewidth}]
# \textbf{d100} & \textbf{Door on the Staircase} & \textbf{Destination}\\

    
if __name__ == "__main__":
    main()
    