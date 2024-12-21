import matplotlib.pyplot as plt
from matplotlib.sankey import Sankey

fig = plt.figure()
ax = fig.add_subplot(xticks=[], yticks=[], title="Estrategias de venta (long)")
sankey = Sankey(ax=ax, scale=0.01, offset=0.2, head_angle=180, format='%.0f')
sankey.add(flows=[0, 0, 30, -30, -30, -40, -50, -50, -0, -100],
           labels=['', '', '', '30%', '30%', '40%', '50%', '50%', '0%', '100%'],
           orientations=[-1, 1, 0, 1, 1, 1, -1, -1, -1, 0],
           pathlengths=[5.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.15],
           patchlabel="Ganancias\nA")
diagrams = sankey.finish()
diagrams[0].texts[-1].set_color('r')
diagrams[0].text.set_fontweight('bold')