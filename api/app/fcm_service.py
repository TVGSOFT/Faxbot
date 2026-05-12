"""Firebase Cloud Messaging (FCM) notification service.

Credentials are loaded per ``app_id`` from environment variables following
the naming convention::

    FCM_CREDENTIALS_<APP_ID_UPPER_SNAKE>

For example, ``app_id = "smart-printer"`` maps to the env var
``FCM_CREDENTIALS_SMART_PRINTER``.  The env var value must be the raw JSON
string of a Firebase service-account credentials file.

Usage::

    from .fcm_service import send_fax_notification
    send_fax_notification(job)  # fire-and-forget, never raises
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Cache of initialised firebase_admin.App instances, keyed by app_id.
_app_cache: Dict[str, Any] = {}

# ---------------------------------------------------------------------------
# Notification message catalogue
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Per-status, per-language message catalogue
# Supported: en (fallback), ar, de, es, fr, hi, id, ko, pt, th, tr, vi
# Body templates use {to} as a placeholder for the destination phone number.
# ---------------------------------------------------------------------------

_STATUS_MESSAGES: Dict[str, Dict[str, Dict[str, str]]] = {
    "SUCCESS": {
        "en": {"title": "Fax Sent Successfully", "body": "Your fax to {to} has been delivered successfully."},
        "ar": {"title": "تم إرسال الفاكس بنجاح", "body": "تم تسليم فاكسك إلى {to} بنجاح."},
        "de": {"title": "Fax erfolgreich gesendet", "body": "Ihr Fax an {to} wurde erfolgreich zugestellt."},
        "es": {"title": "Fax enviado con éxito", "body": "Su fax a {to} ha sido entregado con éxito."},
        "fr": {"title": "Fax envoyé avec succès", "body": "Votre fax à {to} a été livré avec succès."},
        "hi": {"title": "फैक्स सफलतापूर्वक भेजा गया", "body": "{to} को आपका फैक्स सफलतापूर्वक पहुँचा दिया गया।"},
        "id": {"title": "Faks Berhasil Dikirim", "body": "Faks Anda ke {to} telah berhasil terkirim."},
        "ko": {"title": "팩스 전송 성공", "body": "{to}(으)로 보낸 팩스가 성공적으로 전달되었습니다."},
        "pt": {"title": "Fax Enviado com Sucesso", "body": "Seu fax para {to} foi entregue com sucesso."},
        "th": {"title": "ส่งแฟกซ์สำเร็จ", "body": "แฟกซ์ของคุณถึง {to} ได้รับการจัดส่งเรียบร้อยแล้ว"},
        "tr": {"title": "Faks Başarıyla Gönderildi", "body": "{to} numarasına gönderdiğiniz faks başarıyla iletildi."},
        "vi": {"title": "Gửi fax thành công", "body": "Fax của bạn đến {to} đã được gửi thành công."},
    },
    "FAILURE": {
        "en": {"title": "Fax Failed", "body": "Your fax to {to} could not be delivered. Please try again."},
        "ar": {"title": "فشل إرسال الفاكس", "body": "تعذّر تسليم فاكسك إلى {to}. يرجى المحاولة مرة أخرى."},
        "de": {"title": "Fax fehlgeschlagen", "body": "Ihr Fax an {to} konnte nicht zugestellt werden. Bitte versuchen Sie es erneut."},
        "es": {"title": "Error al enviar el fax", "body": "No se pudo entregar su fax a {to}. Por favor, inténtelo de nuevo."},
        "fr": {"title": "Échec de l'envoi du fax", "body": "Votre fax à {to} n'a pas pu être livré. Veuillez réessayer."},
        "hi": {"title": "फैक्स विफल हो गया", "body": "{to} को आपका फैक्स वितरित नहीं हो सका। कृपया पुनः प्रयास करें।"},
        "id": {"title": "Faks Gagal Dikirim", "body": "Faks Anda ke {to} tidak dapat terkirim. Silakan coba lagi."},
        "ko": {"title": "팩스 전송 실패", "body": "{to}(으)로 보낸 팩스를 전달할 수 없었습니다. 다시 시도해 주세요."},
        "pt": {"title": "Falha no Envio do Fax", "body": "Seu fax para {to} não pôde ser entregue. Por favor, tente novamente."},
        "th": {"title": "ส่งแฟกซ์ล้มเหลว", "body": "แฟกซ์ของคุณถึง {to} ไม่สามารถจัดส่งได้ กรุณาลองอีกครั้ง"},
        "tr": {"title": "Faks Gönderilemedi", "body": "{to} numarasına gönderdiğiniz faks teslim edilemedi. Lütfen tekrar deneyin."},
        "vi": {"title": "Gửi fax thất bại", "body": "Fax của bạn đến {to} không thể gửi được. Vui lòng thử lại."},
    },
    "IN_PROGRESS": {
        "en": {"title": "Fax In Progress", "body": "Your fax to {to} is being sent…"},
        "ar": {"title": "جارٍ إرسال الفاكس", "body": "جارٍ إرسال فاكسك إلى {to}…"},
        "de": {"title": "Fax wird gesendet", "body": "Ihr Fax an {to} wird gerade gesendet…"},
        "es": {"title": "Fax en progreso", "body": "Su fax a {to} se está enviando…"},
        "fr": {"title": "Fax en cours d'envoi", "body": "Votre fax à {to} est en cours d'envoi…"},
        "hi": {"title": "फैक्स प्रक्रिया में है", "body": "{to} को आपका फैक्स भेजा जा रहा है…"},
        "id": {"title": "Faks Sedang Dikirim", "body": "Faks Anda ke {to} sedang dikirim…"},
        "ko": {"title": "팩스 전송 중", "body": "{to}(으)로 팩스를 전송 중입니다…"},
        "pt": {"title": "Fax em Andamento", "body": "Seu fax para {to} está sendo enviado…"},
        "th": {"title": "กำลังส่งแฟกซ์", "body": "กำลังส่งแฟกซ์ของคุณถึง {to}…"},
        "tr": {"title": "Faks Gönderiliyor", "body": "{to} numarasına faksınız gönderiliyor…"},
        "vi": {"title": "Đang gửi fax", "body": "Fax của bạn đến {to} đang được gửi…"},
    },
    "QUEUED": {
        "en": {"title": "Fax Queued", "body": "Your fax to {to} has been queued and will be sent shortly."},
        "ar": {"title": "الفاكس في قائمة الانتظار", "body": "تمت إضافة فاكسك إلى {to} في قائمة الانتظار وسيُرسل قريبًا."},
        "de": {"title": "Fax in Warteschlange", "body": "Ihr Fax an {to} wurde in die Warteschlange gestellt und wird in Kürze gesendet."},
        "es": {"title": "Fax en cola", "body": "Su fax a {to} está en cola y se enviará en breve."},
        "fr": {"title": "Fax en attente", "body": "Votre fax à {to} est en file d'attente et sera envoyé sous peu."},
        "hi": {"title": "फैक्स कतार में है", "body": "{to} को आपका फैक्स कतार में है और जल्द ही भेजा जाएगा।"},
        "id": {"title": "Faks Dalam Antrian", "body": "Faks Anda ke {to} telah masuk antrian dan akan segera dikirim."},
        "ko": {"title": "팩스 대기 중", "body": "{to}(으)로 보내는 팩스가 대기열에 추가되었으며 곧 전송됩니다."},
        "pt": {"title": "Fax na Fila", "body": "Seu fax para {to} está na fila e será enviado em breve."},
        "th": {"title": "แฟกซ์อยู่ในคิว", "body": "แฟกซ์ของคุณถึง {to} อยู่ในคิวและจะถูกส่งในไม่ช้า"},
        "tr": {"title": "Faks Sıraya Alındı", "body": "{to} numarasına gönderdiğiniz faks sıraya alındı ve kısa süre içinde gönderilecek."},
        "vi": {"title": "Fax đã vào hàng đợi", "body": "Fax của bạn đến {to} đã được xếp hàng và sẽ được gửi sớm."},
    },
    "SCHEDULED": {
        "en": {"title": "Fax Scheduled", "body": "Your fax to {to} has been scheduled for delivery."},
        "ar": {"title": "تمت جدولة الفاكس", "body": "تمت جدولة إرسال فاكسك إلى {to}."},
        "de": {"title": "Fax geplant", "body": "Ihr Fax an {to} wurde für den Versand geplant."},
        "es": {"title": "Fax programado", "body": "Su fax a {to} ha sido programado para su envío."},
        "fr": {"title": "Fax planifié", "body": "Votre fax à {to} a été planifié pour la livraison."},
        "hi": {"title": "फैक्स शेड्यूल हो गया", "body": "{to} को आपका फैक्स भेजने के लिए शेड्यूल किया गया है।"},
        "id": {"title": "Faks Dijadwalkan", "body": "Faks Anda ke {to} telah dijadwalkan untuk dikirim."},
        "ko": {"title": "팩스 예약됨", "body": "{to}(으)로 보내는 팩스가 전송 예약되었습니다."},
        "pt": {"title": "Fax Agendado", "body": "Seu fax para {to} foi agendado para entrega."},
        "th": {"title": "แฟกซ์ถูกตั้งเวลา", "body": "แฟกซ์ของคุณถึง {to} ถูกตั้งเวลาสำหรับการจัดส่งแล้ว"},
        "tr": {"title": "Faks Planlandı", "body": "{to} numarasına gönderdiğiniz faks teslim için planlandı."},
        "vi": {"title": "Fax đã được lên lịch", "body": "Fax của bạn đến {to} đã được lên lịch gửi."},
    },
}

# Build lowercase aliases automatically so internal statuses resolve correctly.
# Also add common variant spellings (e.g. "failed" → FAILURE, "success" → SUCCESS).
_LOWERCASE_ALIASES = {k.lower(): v for k, v in _STATUS_MESSAGES.items()}
_STATUS_MESSAGES.update({k: v for k, v in _LOWERCASE_ALIASES.items() if k not in _STATUS_MESSAGES})

# Handle variant spellings not covered by the simple lower-case pass
_STATUS_MESSAGES.setdefault("failed", _STATUS_MESSAGES["FAILURE"])
_STATUS_MESSAGES.setdefault("success", _STATUS_MESSAGES["SUCCESS"])
_STATUS_MESSAGES.setdefault("in_progress", _STATUS_MESSAGES["IN_PROGRESS"])
_STATUS_MESSAGES.setdefault("queued", _STATUS_MESSAGES["QUEUED"])
_STATUS_MESSAGES.setdefault("scheduled", _STATUS_MESSAGES["SCHEDULED"])

_FALLBACK_MESSAGE: Dict[str, Dict[str, str]] = {
    "en": {"title": "Fax Update", "body": "Your fax status has been updated."},
    "ar": {"title": "تحديث الفاكس", "body": "تم تحديث حالة فاكسك."},
    "de": {"title": "Fax-Update", "body": "Ihr Fax-Status wurde aktualisiert."},
    "es": {"title": "Actualización de fax", "body": "El estado de su fax ha sido actualizado."},
    "fr": {"title": "Mise à jour du fax", "body": "Le statut de votre fax a été mis à jour."},
    "hi": {"title": "फैक्स अपडेट", "body": "आपके फैक्स की स्थिति अपडेट हो गई है।"},
    "id": {"title": "Pembaruan Faks", "body": "Status faks Anda telah diperbarui."},
    "ko": {"title": "팩스 업데이트", "body": "팩스 상태가 업데이트되었습니다."},
    "pt": {"title": "Atualização de Fax", "body": "O status do seu fax foi atualizado."},
    "th": {"title": "อัปเดตแฟกซ์", "body": "สถานะแฟกซ์ของคุณได้รับการอัปเดตแล้ว"},
    "tr": {"title": "Faks Güncellemesi", "body": "Faks durumunuz güncellendi."},
    "vi": {"title": "Cập nhật fax", "body": "Trạng thái fax của bạn đã được cập nhật."},
}


def _app_id_to_env_key(app_id: str) -> str:
    """Convert app_id to the expected env var name.

    Examples:
        "smart-printer"  → "FCM_CREDENTIALS_SMART_PRINTER"
        "my_app"         → "FCM_CREDENTIALS_MY_APP"
    """
    safe = app_id.upper().replace("-", "_").replace(" ", "_")
    return f"FCM_CREDENTIALS_{safe}"


def _get_firebase_app(app_id: str) -> Optional[Any]:
    """Return (and cache) a ``firebase_admin.App`` for the given ``app_id``.

    Returns ``None`` if:
    - ``firebase_admin`` is not installed
    - The env var is not set or contains invalid JSON
    """
    if app_id in _app_cache:
        return _app_cache[app_id]

    try:
        import firebase_admin  # type: ignore
        from firebase_admin import credentials  # type: ignore
    except ImportError:
        logger.warning("firebase-admin is not installed; FCM notifications disabled")
        return None

    env_key = _app_id_to_env_key(app_id)
    cred_json = os.environ.get(env_key, "").strip()
    if not cred_json:
        logger.warning(
            "FCM credentials env var '%s' is not set for app_id='%s'; skipping FCM",
            env_key,
            app_id,
        )
        return None

    try:
        cred_dict = json.loads(cred_json)
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON in '%s': %s", env_key, exc)
        return None

    try:
        cred = credentials.Certificate(cred_dict)
        # Use a unique name to support multiple apps
        firebase_app_name = f"faxbot_{app_id}"
        try:
            firebase_app = firebase_admin.get_app(firebase_app_name)
        except ValueError:
            firebase_app = firebase_admin.initialize_app(cred, name=firebase_app_name)
        _app_cache[app_id] = firebase_app
        logger.info("Firebase app '%s' initialised for app_id='%s'", firebase_app_name, app_id)
        return firebase_app
    except Exception as exc:
        logger.error("Failed to initialise Firebase app for app_id='%s': %s", app_id, exc)
        return None


def _get_message_texts(status: str, language: str, to_number: str = "") -> Dict[str, str]:
    """Return ``{"title": ..., "body": ...}`` for the given status and language.

    The ``{to}`` placeholder in body strings is replaced with ``to_number``.
    Language falls back to ``en`` when the requested code is not available.
    """
    lang = (language or "en").strip().lower()
    status_map = _STATUS_MESSAGES.get(status, {})
    texts = status_map.get(lang) or status_map.get("en")
    if not texts:
        texts = _FALLBACK_MESSAGE.get(lang) or _FALLBACK_MESSAGE["en"]
    # Substitute {to} placeholder (copy so the catalogue is not mutated)
    display_to = to_number or ""
    return {
        "title": texts["title"],
        "body": texts["body"].replace("{to}", display_to),
    }


def send_fax_notification(job: Any) -> None:
    """Push an FCM notification for the given ``FaxJob`` instance.

    This function is intentionally non-raising — all errors are logged and
    swallowed so a notification failure never disrupts the fax pipeline.

    The job must have the following attributes:
        - ``fcm_token`` (str | None): device FCM registration token
        - ``app_id``    (str | None): application identifier
        - ``id``        (str):        job id
        - ``status``    (str):        current fax status
        - ``language``  (str | None): BCP-47 language code (e.g. "en", "vi")
    """
    try:
        fcm_token: Optional[str] = getattr(job, "fcm_token", None)
        if not fcm_token:
            return  # no token — nothing to do

        app_id: Optional[str] = getattr(job, "app_id", None)
        if not app_id:
            logger.debug("FCM: job %s has no app_id — skipping notification", job.id)
            return

        firebase_app = _get_firebase_app(app_id)
        if not firebase_app:
            return

        try:
            from firebase_admin import messaging  # type: ignore
        except ImportError:
            return

        status: str = str(getattr(job, "status", "") or "")
        language: str = str(getattr(job, "language", "") or "en")
        to_number: str = str(getattr(job, "to_number", "") or "")
        texts = _get_message_texts(status, language, to_number)

        message = messaging.Message(
            notification=messaging.Notification(
                title=texts["title"],
                body=texts["body"],
            ),
            data={
                "type": "fax",
                "job_id": str(job.id),
                "status": status,
                "language": language,
                "to": to_number,
            },
            token=fcm_token,
            android=messaging.AndroidConfig(priority="high"),
            apns=messaging.APNSConfig(
                headers={"apns-priority": "10"},
            ),
        )

        response = messaging.send(message, app=firebase_app)
        logger.info(
            "FCM notification sent: job_id=%s status=%s app_id=%s message_id=%s",
            job.id,
            status,
            app_id,
            response,
        )
    except Exception as exc:
        logger.error(
            "FCM notification failed for job_id=%s: %s",
            getattr(job, "id", "unknown"),
            exc,
        )

