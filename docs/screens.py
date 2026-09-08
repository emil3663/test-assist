"""Report what Qt sees — the same data the app uses to decide where to grab."""
from PySide6.QtWidgets import QApplication
app = QApplication([])
print(f"screens: {len(app.screens())}")
print(f"virtual desktop: {app.primaryScreen().virtualGeometry().getRect()}")
for i, s in enumerate(app.screens()):
    g = s.geometry().getRect()
    a = s.availableGeometry().getRect()
    print(f"\n[{i}] {s.name()}{'  <-- PRIMARY' if s is app.primaryScreen() else ''}")
    print(f"    geometry        x={g[0]} y={g[1]} w={g[2]} h={g[3]}")
    print(f"    available       x={a[0]} y={a[1]} w={a[2]} h={a[3]}")
    print(f"    devicePixelRatio {s.devicePixelRatio()}   (1.0=100%, 1.5=150%)")
    print(f"    logical DPI      {s.logicalDotsPerInch():.0f}")
