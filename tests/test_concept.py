import os
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from fastapi import FastAPI

from api.routes import concept, predict


def make_test_app():
    app = FastAPI()
    app.include_router(concept.router, prefix="/api")
    app.include_router(predict.router, prefix="/api")
    return app


class ConceptRoutesTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(make_test_app())
        self.payload = {
            "lotArea": 300,
            "frontage": 10,
            "buildArea": 165,
            "floors": 2,
            "typology": "casa",
            "finish": "medio",
            "style": "contemporaneo",
            "zone": "ZM",
            "residentialScore": 72,
            "commercialScore": 48,
            "riskLevel": "baixo",
            "growthSignal": 0.002,
        }

    def test_analyze_returns_plan_and_scenarios(self):
        res = self.client.post("/api/concept/analyze", json=self.payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("plan", data)
        self.assertEqual(len(data["scenarios"]), 3)
        self.assertGreater(data["plan"]["viabilityScore"], 0)

    @patch.dict(os.environ, {"HF_TOKEN": ""}, clear=False)
    def test_generate_image_without_token_is_controlled(self):
        res = self.client.post("/api/concept/generate-image", json={**self.payload, "view": "fachada"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "missing_token")
        self.assertIsNone(data["image"])

    def test_report_returns_pdf(self):
        res = self.client.post("/api/concept/report", json=self.payload)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["content-type"], "application/pdf")
        self.assertTrue(res.content.startswith(b"%PDF"))


class PriceFallbackTest(unittest.TestCase):
    def test_predict_uses_fallback_when_model_missing(self):
        from api.routes import predict

        old = predict.MODEL_PATH
        predict.MODEL_PATH = str(Path("models") / "__missing_price_model__.joblib")
        try:
            client = TestClient(make_test_app())
            res = client.post("/api/predict", json={
                "area_m2": 120,
                "bedrooms": 3,
                "bathrooms": 2,
                "parking_spaces": 1,
                "property_type": "casa",
                "latitude": -22.23,
                "longitude": -45.95,
            })
        finally:
            predict.MODEL_PATH = old

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["model_status"], "fallback_hedonic")
        self.assertGreater(data["predicted_price"], 0)
        self.assertGreater(data["price_high"], data["price_low"])


if __name__ == "__main__":
    unittest.main()
