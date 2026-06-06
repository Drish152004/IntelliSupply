from ml_services.coordinate_mapping import build_default_mvp_mapper, WGS84Point

mapper = build_default_mvp_mapper()
synthetic = mapper.to_synthetic(WGS84Point(lat=31.2304, lng=121.4737))
print(synthetic)
# synthetic.lat / synthetic.lng are in your model-trained bounds