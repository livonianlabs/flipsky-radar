# FlipSky radar frames

Observed precipitation for the map in FlipSky (a flip clock and weather app by Livonian Labs): every few minutes a
GitHub Actions job turns the public radar composites of the last two hours into small lat/lon frames and publishes
them to Cloudflare R2, served read-only by a Worker.

- **Europe:** EUMETNET OPERA rain-rate composite, CC BY 4.0 (`opera.py`).
- **USA:** NOAA NEXRAD base reflectivity composite via the Iowa Environmental Mesonet, public domain (`us.py`).

Frame format: an 8-bit grayscale PNG on a plate carrée grid at 0.025°; 0 no radar coverage, 1 dry, 2–255 rain rate
`0.05 * 2^((v-2)/25)` mm/h. `eu.json` / `us.json` list the frames with their bounding box and attribution.

© 2026 Livonian Labs, Riga, Latvia · livonianlabs@gmail.com
