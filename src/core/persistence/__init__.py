"""Phase 87 Stage 2: 永続化基盤

Firestore-backed key-value state store with local JSON fallback.
Cloud Run の ephemeral FS で消失する状態（SL注文ID・ドローダウン・MLヘルス）を
Firestore に永続化することで、Container 再起動から保護する。
"""

from .firestore_state import FirestoreStateClient

__all__ = ["FirestoreStateClient"]
