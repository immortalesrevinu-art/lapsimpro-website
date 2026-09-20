# LapSimPro house livery asset drop

Public gallery: [`/liveries.html`](../../liveries.html)  
Overlay manifest: [`/data/liveries.json`](../../data/liveries.json) (`lapsimpro.liveries.v1`)

Real TGA paint files are **not** in this repo yet. Each folder below is the drop path. After you add files, set the matching `files.*` URLs and `assets_ready: true` in the manifest so the overlay installer will copy them.

## Folder names = iRacing `car_path`

iRacing loads custom paints from:

```text
{Documents}/iRacing/paint/{car_path}/car_{customerId}.tga
{Documents}/iRacing/paint/{car_path}/car_spec_{customerId}.tga
```

Website drop path (GitHub Pages):

```text
assets/liveries/{car_path}/car.tga
assets/liveries/{car_path}/car_spec.tga
assets/liveries/{car_path}/preview.svg   # or preview.png — gallery only
```

| Display name | Catalog id | `car_path` | Aliases |
| --- | --- | --- | --- |
| Ferrari 296 GT3 | `ferrari-296-gt3` | `ferrari296gt3` | |
| Ford Mustang GT3 | `mustang-gt3` | `fordmustanggt3` | |
| BMW M4 GT3 EVO | `bmw-m4-gt3` | `bmwm4gt3` | `bmwm4gt3evo` |
| Lamborghini Huracán GT3 EVO | `huracan-gt3-evo` | `lamborghinievogt3` | |
| Porsche 911 GT3 R | `porsche-992-gt3r` | `porsche992rgt3` | |
| McLaren 720S GT3 EVO | `mclaren-720s` | `mclaren720sgt3` | |
| Mercedes-AMG GT3 | `amg-gt3` | `mercedesamgevogt3` | |

`car_path` values match the [iRacing active-car filepath list](https://support.iracing.com/support/solutions/articles/31000172625-filepath-for-active-iracing-cars) (May 2026). BMW’s EVO update kept the `bmwm4gt3` folder; the alias is there if a later build splits it.

## TGA rules (iRacing)

- 24-bit TGA with RLE for the main paint (`car.tga`)
- Spec map as 24-bit (or 32-bit with alpha) `car_spec.tga`
- Optional `car_num.tga` (custom numbers) and `decal.tga` (32-bit)
- Do **not** bake a customer id into the dropped filename. The overlay installer renames to `car_{id}.tga` at copy time.

## Overlay handshake

Customer Download buttons must stay on lapsimpro.com / the app protocol. They must **not** point at GitHub.

```text
lapsimpro://paint/install?id=<livery_id>&car_path=<car_path>&pack=lapsimpro-house-gt3
```

Fallback if the protocol is not registered yet: `./download.html?paint=<livery_id>` (install the Windows overlay first).

Contract helper the overlay can vendor: `overlay/lapsimpro_sync/paints.py`.
