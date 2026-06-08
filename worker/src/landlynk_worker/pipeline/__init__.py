"""The worker pipeline stages, in order.

1. resolve   - input to WGS84 coordinate (postcode or grid ref)
2. isochrone - drive-time polygon, cached by coordinate and parameters
3. intersect - which boundaries overlap the polygon, and by what proportion
4. join      - pull ONS demographics, tenure and income for retained areas
5. score     - profile and prioritise each area (scoring package)
6. assemble  - build the Battlecard payload per area
7. outputs   - KML now, PDF and PPTX prepared for export
"""
