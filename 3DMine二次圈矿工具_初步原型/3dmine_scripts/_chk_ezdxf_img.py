# -*- coding: utf-8 -*-
import ezdxf, inspect, sys
out = []
out.append(f"ezdxf {ezdxf.__version__}")
doc = ezdxf.new("R2010")
msp = doc.modelspace()
found = False
for klass in type(msp).__mro__:
    if "add_image" in vars(klass):
        out.append(f"add_image in {klass.__name__}")
        try:
            out.append(str(inspect.signature(getattr(klass, "add_image"))))
        except Exception as e:
            out.append(f"sig err {e}")
        found = True
if not found:
    out.append("add_image not found in MRO")
# try doc.add_image_def
out.append("doc has add_image_def: " + str(hasattr(doc, "add_image_def")))
try:
    out.append(str(inspect.signature(doc.add_image_def)))
except Exception as e:
    out.append(f"def sig err: {e}")
sys.stdout.buffer.write("\n".join(out).encode("utf-8"))
