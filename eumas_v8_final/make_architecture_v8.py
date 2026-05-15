import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, axes = plt.subplots(2, 1, figsize=(11.5, 7.0), dpi=220)
fig.patch.set_facecolor('white')

def setup(ax):
    ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis('off')

def box(ax, x, y, w, h, text, fc, ec, fs=8.0, color='black'):
    patch = FancyBboxPatch((x,y), w, h, boxstyle='round,pad=0.018,rounding_size=0.035', fc=fc, ec=ec, lw=1.4)
    ax.add_patch(patch)
    ax.text(x+w/2, y+h/2, text, ha='center', va='center', fontsize=fs, color=color, wrap=True)
    return patch

def arrow(ax, start, end, color='black', style='solid', rad=0.0, lw=1.35):
    ls = '-' if style == 'solid' else '--' if style == 'dashed' else ':'
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle='-|>', mutation_scale=10, lw=lw, linestyle=ls,
                                 color=color, connectionstyle=f'arc3,rad={rad}'))

# Panel A - clear clockwise pipeline with minimal crossing
ax = axes[0]; setup(ax)
ax.text(0.02, 0.96, 'A. Conceptual emotionally bounded-rational loop', fontsize=11, fontweight='bold', va='top')
blue = ('#eef5ff', '#1b4f72')
orange = ('#fff4e6', '#9a5a00')
purple = ('#f4ecff', '#5b2c6f')
green = ('#eafaf1', '#196f3d')
# top row
nodes = [
    (0.03,0.62,0.15,0.20,'External game\noutcome + payoff'),
    (0.22,0.62,0.15,0.20,'Game-to-values\nadapter'),
    (0.41,0.62,0.15,0.20,'Event values\nmat/fair/rel/safe'),
    (0.60,0.62,0.15,0.20,'Appraisal\nurgency / load / focus'),
    (0.79,0.62,0.16,0.20,'Internal state\nmood / fatigue / w'),
]
for x,y,w,h,t in nodes:
    box(ax,x,y,w,h,t,*blue,fs=7.7)
for (x,y,w,h,_),(x2,y2,w2,h2,_) in zip(nodes, nodes[1:]):
    arrow(ax,(x+w, y+h/2),(x2, y2+h2/2), color=blue[1])
# control row
box(ax,0.25,0.22,0.18,0.20,'System 1\nemotional proposal',*orange,fs=7.8)
box(ax,0.52,0.22,0.20,0.20,'System 2\naccept / override\n/ refocus',*purple,fs=7.7)
box(ax,0.80,0.22,0.14,0.20,'Final\naction',*green,fs=7.8)
# straight/down arrows, no mixing
arrow(ax,(0.87,0.62),(0.87,0.42),color=green[1])
arrow(ax,(0.80,0.32),(0.72,0.32),color=green[1])
arrow(ax,(0.52,0.32),(0.43,0.32),color=purple[1])
# From internal state/appraisal to System 1 (clean left-to-right path under row)
arrow(ax,(0.675,0.62),(0.34,0.42),color=orange[1],rad=0.12)
arrow(ax,(0.43,0.32),(0.52,0.32),color=purple[1])
arrow(ax,(0.72,0.32),(0.80,0.32),color=green[1])
# feedback from final action to next game outcome below boxes
arrow(ax,(0.87,0.22),(0.105,0.62),style='dashed',color='#666666',rad=-0.35,lw=1.2)
ax.text(0.07,0.12,'Dashed feedback: final action affects the next game outcome.', fontsize=7.4, color='#555555')

# Panel B
ax = axes[1]; setup(ax)
ax.text(0.02, 0.96, 'B. Implementation status in the paper runs', fontsize=11, fontweight='bold', va='top')
box(ax,0.08,0.58,0.20,0.22,'Implemented\ncontrol flow\nlearned agents + games', '#e8f8f5', '#117a65', fs=7.8)
box(ax,0.36,0.58,0.20,0.22,'Behavior-driving\nstate variables\nmood / fatigue / w / S', '#e8f8f5', '#117a65', fs=7.8)
box(ax,0.64,0.58,0.18,0.22,'Diagnostic\nvariables\nadapter + appraisal logs', '#fff9e6', '#b9770e', fs=7.8)
box(ax,0.63,0.20,0.20,0.18,'Future only\nwhite-box agent,\nbelief update', '#f2f3f4', '#7b7d7d', fs=7.6, color='#444444')
arrow(ax,(0.28,0.69),(0.36,0.69),color='#117a65')
arrow(ax,(0.56,0.69),(0.64,0.69),style='dashed',color='#b9770e')
arrow(ax,(0.73,0.58),(0.73,0.38),style='dotted',color='#7b7d7d')
# legend
box(ax,0.10,0.22,0.14,0.15,'solid\nbehavior', 'white', '#117a65', fs=7.4)
box(ax,0.30,0.22,0.14,0.15,'dashed\ndiagnostic', 'white', '#b9770e', fs=7.4)
box(ax,0.46,0.22,0.12,0.15,'dotted\nfuture', '#f2f3f4', '#7b7d7d', fs=7.4)
ax.text(0.08,0.08,'Diagnostic variables are computed from logged outcomes to interpret runs; they do not feed back into action selection in these paper-profile experiments.', fontsize=7.2, color='#444444')

plt.tight_layout(pad=0.7)
for ext in ('png','pdf'):
    fig.savefig(f'/mnt/data/eumas_v8_work/figures/architecture_concept_status_v8.{ext}', bbox_inches='tight')
