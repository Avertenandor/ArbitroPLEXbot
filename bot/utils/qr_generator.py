"""
QR code generator utility.

Generates QR codes for wallet addresses and payment information.
"""

import io

import qrcode
from loguru import logger
from qrcode.image.pil import PilImage


def generate_wallet_qr(
    wallet_address: str,
    box_size: int = 10,
    border: int = 2,
) -> bytes | None:
    """
    Generate QR code image for a wallet address.

    Args:
        wallet_address: BSC/ETH wallet address (0x...)
        box_size: Size of each box in pixels
        border: Border size in boxes

    Returns:
        PNG image as bytes, or None if generation fails
    """
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=box_size,
            border=border,
        )
        qr.add_data(wallet_address)
        qr.make(fit=True)

        img: PilImage = qr.make_image(fill_color="black", back_color="white")

        # Save to bytes
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        return buffer.getvalue()

    except Exception as e:
        logger.error(f"Failed to generate QR code: {e}")
        return None


def generate_payment_qr(
    wallet_address: str,
    token_address: str | None = None,
    amount: int | None = None,
) -> bytes | None:
    """
    Generate QR code for payment.

    For simplicity, just encodes the wallet address.
    Most wallets will recognize and allow sending to this address.

    Args:
        wallet_address: Destination wallet address
        token_address: Token contract address (for reference)
        amount: Amount to send (for reference)

    Returns:
        PNG image as bytes, or None if generation fails
    """
    # For BEP-20/ERC-20 transfers, most wallets just need the destination address
    # The user selects the token and amount in their wallet app
    return generate_wallet_qr(wallet_address)
