# Software render of a .glb (single mesh, uncompressed) to a transparent image: orthographic front view,
# z-buffered, base-colour texture, optionally with simple lighting. Usage: python3 -I render.py in.glb out.png [front|back] [unlit]
import struct, json, sys, io
import numpy as np, cv2
from PIL import Image
src, out, side = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else 'front')
unlit = 'unlit' in sys.argv[4:]   # unlit: the model's own colours with no added lighting
raw = open(src, 'rb').read()
clen = struct.unpack('<I', raw[12:16])[0]; js = json.loads(raw[20:20+clen]); binoff = 20 + clen + 8
def view(i): bv = js['bufferViews'][i]; o = binoff + bv.get('byteOffset', 0); return raw[o:o+bv['byteLength']], bv
def acc(i):
    a = js['accessors'][i]; data, bv = view(a['bufferView'])
    dt = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8}[a['componentType']]
    n = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[a['type']]
    stride = bv.get('byteStride') or np.dtype(dt).itemsize * n
    off = a.get('byteOffset', 0)
    if stride == np.dtype(dt).itemsize * n:
        arr = np.frombuffer(data, dt, a['count'] * n, off).reshape(a['count'], n)
    else:
        arr = np.stack([np.frombuffer(data, dt, n, off + k * stride) for k in range(a['count'])])
    return arr
prim = js['meshes'][0]['primitives'][0]; at = prim['attributes']
P = acc(at['POSITION']).astype(np.float64); Nrm = acc(at['NORMAL']).astype(np.float32); UV = acc(at['TEXCOORD_0']).astype(np.float32)
I = acc(prim['indices']).reshape(-1, 3).astype(np.int64)
mat = js['materials'][prim['material']]; ti = mat['pbrMetallicRoughness']['baseColorTexture']['index']
img = js['images'][js['textures'][ti]['source']]
tex = np.asarray(Image.open(io.BytesIO(view(img['bufferView'])[0])).convert('RGB')).astype(np.float32) / 255
if side == 'back': P = P * np.array([-1, 1, -1]); Nrm = Nrm * np.array([-1, 1, -1], np.float32)
FINAL, SS = 640, 3; W = H = FINAL * SS
mn, mx = P.min(0), P.max(0); c = (mn + mx) / 2; scale = W * 0.94 / max(mx[0]-mn[0], mx[1]-mn[1])
sx = (P[:, 0] - c[0]) * scale + W / 2; sy = H / 2 - (P[:, 1] - c[1]) * scale; sz = P[:, 2]
x0, y0, x1, y1, x2, y2 = sx[I[:, 0]], sy[I[:, 0]], sx[I[:, 1]], sy[I[:, 1]], sx[I[:, 2]], sy[I[:, 2]]
area = (x1-x0)*(y2-y0) - (x2-x0)*(y1-y0)
keep = area < -1e-9            # front-facing once the y axis is flipped for the screen
I = I[keep]; area = area[keep]; x0, y0, x1, y1, x2, y2 = (v[keep] for v in (x0, y0, x1, y1, x2, y2))
bx0 = np.floor(np.minimum(np.minimum(x0, x1), x2)).astype(np.int64); by0 = np.floor(np.minimum(np.minimum(y0, y1), y2)).astype(np.int64)
bx1 = np.floor(np.maximum(np.maximum(x0, x1), x2)).astype(np.int64); by1 = np.floor(np.maximum(np.maximum(y0, y1), y2)).astype(np.int64)
size = np.maximum(bx1-bx0, by1-by0) + 1
zbuf = np.full(W*H, -1e9, np.float32); tri = np.full(W*H, -1, np.int64); bary = np.zeros((W*H, 3), np.float32)
z0, z1, z2 = sz[I[:, 0]], sz[I[:, 1]], sz[I[:, 2]]
print('front-facing triangles', len(I), 'max bbox', size.max())
lo = 0
for K in (4, 8, 16, 32, 64, 128, 4096):
    sel = np.where((size > lo) & (size <= K))[0]; lo = K
    if not len(sel): continue
    Kc = min(K, int(size[sel].max()))
    step = max(1, int(4e6 // (Kc*Kc)))
    gy, gx = np.mgrid[0:Kc, 0:Kc]
    for s in range(0, len(sel), step):
        t = sel[s:s+step]
        px = bx0[t][:, None, None] + gx[None] ; py = by0[t][:, None, None] + gy[None]
        fx = px + 0.5; fy = py + 0.5
        def edge(ax, ay, bx, by): return (bx-ax)[:, None, None]*(fy-ay[:, None, None]) - (by-ay)[:, None, None]*(fx-ax[:, None, None])
        w0 = edge(x1[t], y1[t], x2[t], y2[t]) / area[t][:, None, None]
        w1 = edge(x2[t], y2[t], x0[t], y0[t]) / area[t][:, None, None]
        w2 = 1 - w0 - w1
        inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0) & (px >= 0) & (px < W) & (py >= 0) & (py < H)
        ti_, iy, ix = np.nonzero(inside)
        if not len(ti_): continue
        a, b, cc = w0[inside], w1[inside], w2[inside]
        tt = t[ti_]; z = (a*z0[tt] + b*z1[tt] + cc*z2[tt]).astype(np.float32)
        pix = py[inside]*W + px[inside]
        better = z > zbuf[pix]
        pix, z, tt, a, b, cc = pix[better], z[better], tt[better], a[better], b[better], cc[better]
        o = np.argsort(z, kind='stable')
        zbuf[pix[o]] = z[o]; tri[pix[o]] = tt[o]; bary[pix[o]] = np.stack([a[o], b[o], cc[o]], 1)
cov = tri >= 0; T = I[tri[cov]]; B = bary[cov]
uv = (UV[T] * B[:, :, None]).sum(1); n = (Nrm[T] * B[:, :, None]).sum(1); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
th, tw = tex.shape[:2]
u = np.clip(uv[:, 0]*tw - 0.5, 0, tw - 1.001); v = np.clip(uv[:, 1]*th - 0.5, 0, th - 1.001)
iu = u.astype(np.int64); iv = v.astype(np.int64); fu = (u - iu)[:, None]; fv = (v - iv)[:, None]
col = (tex[iv, iu]*(1-fu) + tex[iv, iu+1]*fu)*(1-fv) + (tex[iv+1, iu]*(1-fu) + tex[iv+1, iu+1]*fu)*fv
L = np.array([0.25, 0.45, 1.0], np.float32); L /= np.linalg.norm(L)
shade = np.ones(len(n), np.float32) if unlit else 0.62 + 0.5 * np.clip(n @ L, 0, 1)
rgba = np.zeros((W*H, 4), np.float32); rgba[cov, :3] = np.clip(col * shade[:, None], 0, 1); rgba[cov, 3] = 1
rgba = rgba.reshape(H, W, 4); rgba[..., :3] *= rgba[..., 3:]
small = cv2.resize(rgba, (FINAL, FINAL), interpolation=cv2.INTER_AREA)
al = small[..., 3:]; small[..., :3] = np.where(al > 1e-4, small[..., :3] / np.maximum(al, 1e-4), 0)
Image.fromarray((np.clip(small, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA').save(out, quality=92)
print('saved', out, 'coverage', float(cov.mean()))
