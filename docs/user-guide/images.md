# Images

Studiorum can put 5etools artwork into the documents it builds: plates and maps in adventures and books, galleries, fluff art for creatures, spells and items, and creature tokens.

## Getting the images

The images live in a checkout of [5etools-img](https://github.com/5etools-mirror-3/5etools-img), which 5etools image paths are relative to. If the checkout is at `~/Code/5etools-img`, Studiorum finds it without any configuration. Anywhere else, set `image.image_directory`:

```yaml
image:
  image_directory: ~/src/5etools-img
```

Every image in 5etools-img is WebP, which no LaTeX engine can read. Studiorum converts each one to PNG the first time a document uses it, scaled down to 2,400 pixels wide, and keeps the PNG in the cache directory. Later builds reuse it. Images with an external URL (some homebrew tokens) are downloaded into the same cache once.

The cache is `images/` under the Studiorum cache directory (`$STUDIORUM_CACHE_DIR`, or the platform's user cache folder). Set `image.cache_dir` to put it somewhere else. PNG files are a few times larger than the WebP originals, so a large adventure can take a few hundred megabytes.

## Turning images on

Images are off by default. Pass `--images` to a convert command, or set `image.include_images: true` to make that the default:

```bash
studiorum convert adventure lmop --images
studiorum convert creatures Goblin Aboleth --sources mm --fluff --with-fluff-images --images
studiorum convert spells Barkskin Fireball --sources phb --fluff --with-fluff-images --images
studiorum convert items "Alchemy Jug" --fluff --with-fluff-images --images
```

With images off, each image becomes a `% Image placeholder` comment. An image that can't be found becomes `% Image not found: <path>`.

Fluff images need `--fluff` and `--with-fluff-images` as well as `--images`. A creature's images appear after its fluff text and before its statblock; a spell's and an item's appear after the description.

## How images are placed

Each 5etools image entry becomes one of the Studiorum image commands, defined in `_studiorum_image_macros.tex.j2`:

| Command | Used for |
| --- | --- |
| `\StudiorumImageWide` | Maps (`imageType` of `map` or `mapPlayer`): a float across both columns |
| `\StudiorumImageInline` | Every other image: centred in the column where it appears |

The image's title becomes its caption, and the starred form (`\StudiorumImageInline*`) is used when there is no title. Every image is scaled to the column (or page) width and capped at 0.45 of the text height. A label (`fig:<id>`) is added only when the 5etools entry has an `id`.

A 5etools gallery becomes a figure with a two-column grid of subfigures, each with its own caption.

The macros file also defines `\StudiorumImageFloat`, `\StudiorumImageFullpage` and `\StudiorumImageFullpageBleed`, plus a `NoCaption` form of each, for your own LaTeX. Each takes an optional width fraction, the file, the caption and an optional label:

```latex
\StudiorumImageFloat[.8]{art/tavern.png}{The Yawning Portal}[fig:tavern]
\StudiorumImageFullpageNoCaption{art/map.png}
```

## Tokens

`convert creatures --tokens` builds a printable sheet of round tokens. Each creature's token is found where 5etools looks for it (its `token` or `tokenHref`, otherwise `bestiary/tokens/<source>/<name>.webp`). A creature with no token uses its bestiary art, and one with neither gets an empty circle.

## Troubleshooting

`% Image not found` lines mean the file isn't under `image_directory`. Check the path in the comment against your checkout; a partial or out-of-date clone is the usual cause.

A slow first build is the WebP conversion. Later builds of the same document reuse the cached PNGs.
