# WORKFLOW: Logistic regression calibrator for HS classification confidence.
# Used by: RAG pipeline, HS classification, abstention decisions
# Functions:
# 1. predict_confidence() - Predict confidence score from features
# 2. should_abstain() - Decide whether to abstain from classification
# 3. train() - Train calibrator on labeled data
# 4. get_confidence_and_abstain() - Combined confidence and abstention
#
# Calibration flow: Reranked features -> Confidence prediction -> Abstention decision
# This is the fourth step in RAG: features -> confidence score -> classify/abstain
# Thresholds: confidence ≥0.62 & margin ≥0.07 for classification
# Prevents low-confidence classifications and enables clarification requests.

"""Confidence calibration utilities for HS classification.

This module uses scikit-learn for logistic regression but imports it lazily so
the rest of the application can operate without the heavy dependency during
tests or lightweight deployments.
"""

import numpy as np
import pickle
import logging
from typing import List, Tuple
from pathlib import Path
from core.config import settings

logger = logging.getLogger(__name__)


class ConfidenceCalibrator:
    """Logistic regression calibrator for HS classification confidence."""
    
    def __init__(self, model_path: str = "models/calibrator.pkl"):
        self.model_path = Path(model_path)
        self.model = None
        self.scaler = None
        self.is_trained = False
        self._load_model()
    
    def _load_model(self):
        """Load pre-trained model if available."""
        try:
            from sklearn.linear_model import LogisticRegression
            from sklearn.preprocessing import StandardScaler

            if self.model_path.exists():
                with open(self.model_path, 'rb') as f:
                    model_data = pickle.load(f)
                    self.model = model_data['model']
                    self.scaler = model_data['scaler']
                    self.is_trained = True
                logger.info(f"Loaded pre-trained calibrator from {self.model_path}")
            else:
                self.model = LogisticRegression(random_state=42, max_iter=1000)
                self.scaler = StandardScaler()
                logger.info("Initialized new calibrator model")
        except Exception as e:
            logger.error(f"Failed to load calibrator model: {e}")
            from sklearn.linear_model import LogisticRegression
            from sklearn.preprocessing import StandardScaler

            self.model = LogisticRegression(random_state=42, max_iter=1000)
            self.scaler = StandardScaler()
    
    def _save_model(self):
        """Save the trained model."""
        try:
            self.model_path.parent.mkdir(parents=True, exist_ok=True)
            model_data = {
                'model': self.model,
                'scaler': self.scaler
            }
            with open(self.model_path, 'wb') as f:
                pickle.dump(model_data, f)
            logger.info(f"Saved calibrator model to {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to save calibrator model: {e}")
    
    def train(self, features: List[List[float]], labels: List[int]) -> None:
        """
        Train the calibrator model.
        
        Args:
            features: List of feature vectors [top1, top2, gap, mean, std]
            labels: List of binary labels (1 for correct, 0 for incorrect)
        """
        try:
            if len(features) != len(labels):
                raise ValueError("Features and labels must have the same length")

            from sklearn.model_selection import train_test_split
            from sklearn.metrics import accuracy_score, precision_recall_fscore_support
            from sklearn.preprocessing import StandardScaler

            # Convert to numpy arrays
            X = np.array(features)
            y = np.array(labels)

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )

            # Scale features
            self.scaler = self.scaler or StandardScaler()
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)

            # Train model
            self.model.fit(X_train_scaled, y_train)

            # Evaluate
            y_pred = self.model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            precision, recall, f1, _ = precision_recall_fscore_support(
                y_test, y_pred, average="binary"
            )

            logger.info("Calibrator training results:")
            logger.info(f"  Accuracy: {accuracy:.3f}")
            logger.info(f"  Precision: {precision:.3f}")
            logger.info(f"  Recall: {recall:.3f}")
            logger.info(f"  F1-Score: {f1:.3f}")
            
            self.is_trained = True
            self._save_model()
            
        except Exception as e:
            logger.error(f"Calibrator training failed: {e}")
            raise
    
    def predict_confidence(self, features: List[float]) -> float:
        """
        Predict confidence score for given features.
        
        Args:
            features: Feature vector [top1, top2, gap, mean, std]
            
        Returns:
            Confidence score between 0 and 1
        """
        try:
            if not self.is_trained:
                logger.warning("Calibrator not trained, using default confidence")
                return 0.5
            
            # Convert to numpy array and reshape
            X = np.array(features).reshape(1, -1)
            
            # Scale features
            X_scaled = self.scaler.transform(X)
            
            # Predict probability
            confidence = self.model.predict_proba(X_scaled)[0][1]  # Probability of correct classification
            
            return float(confidence)
            
        except Exception as e:
            logger.error(f"Confidence prediction failed: {e}")
            return 0.5  # Default confidence
    
    def should_abstain(self, confidence: float, margin: float) -> bool:
        """
        Determine if the model should abstain from classification.
        
        Args:
            confidence: Predicted confidence score
            margin: Margin between top1 and top2 scores
            
        Returns:
            True if should abstain, False otherwise
        """
        try:
            # Check confidence threshold
            if confidence < settings.confidence_threshold:
                return True
            
            # Check margin threshold
            if margin < settings.margin_threshold:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Abstention decision failed: {e}")
            return True  # Default to abstaining
    
    def get_confidence_and_abstain(self, features: List[float], margin: float) -> Tuple[float, bool]:
        """
        Get confidence score and abstention decision.
        
        Args:
            features: Feature vector [top1, top2, gap, mean, std]
            margin: Margin between top1 and top2 scores
            
        Returns:
            Tuple of (confidence_score, should_abstain)
        """
        try:
            confidence = self.predict_confidence(features)
            should_abstain = self.should_abstain(confidence, margin)
            
            return confidence, should_abstain
            
        except Exception as e:
            logger.error(f"Confidence and abstention decision failed: {e}")
            return 0.5, True  # Default values
    
    def update_model(self, new_features: List[List[float]], new_labels: List[int]) -> None:
        """
        Update the model with new training data.
        
        Args:
            new_features: New feature vectors
            new_labels: New binary labels
        """
        try:
            if not self.is_trained:
                # If not trained, just train with new data
                self.train(new_features, new_labels)
                return
            
            # Combine with existing data (if available)
            # For now, retrain with new data only
            # In production, you might want to implement incremental learning
            self.train(new_features, new_labels)
            
        except Exception as e:
            logger.error(f"Model update failed: {e}")
            raise


# Global calibrator instance
calibrator = ConfidenceCalibrator()
