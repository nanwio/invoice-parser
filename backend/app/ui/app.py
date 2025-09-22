# Copyright 2024 Artificial Intelligence Labs, SL

import time
import json
import hashlib
import gradio as gr

from loguru import logger
from jose import jwt

from app.services.parser.parser import InvoiceParser
from app.services.cache import cache_service
from app.services.classifier import document_classifier
from app.services.parser.models import Invoice
from app.settings import settings


# Initialize parser
parser = InvoiceParser()


def format_invoice_result(invoice: Invoice) -> str:
    """
    Format invoice data for display.
    """
    result = "## Parsed Invoice Data\n\n"

    # Metadata
    if invoice.metadata:
        result += "### Invoice Information\n"
        if invoice.metadata.invoice_number:
            result += f"- **Invoice Number:** {invoice.metadata.invoice_number}\n"
        if invoice.metadata.issue_date:
            result += f"- **Issue Date:** {invoice.metadata.issue_date}\n"
        if invoice.metadata.due_date:
            result += f"- **Due Date:** {invoice.metadata.due_date}\n"
        if invoice.metadata.order_number:
            result += f"- **Order Number:** {invoice.metadata.order_number}\n"
        result += "\n"

    # Parties
    result += "### Parties\n"
    result += f"**Vendor:** {invoice.parties.vendor.name}\n"
    if invoice.parties.vendor.tax_id:
        result += f"- Tax ID: {invoice.parties.vendor.tax_id}\n"
    result += f"\n**Customer:** {invoice.parties.customer.name}\n"
    if invoice.parties.customer.tax_id:
        result += f"- Tax ID: {invoice.parties.customer.tax_id}\n"
    result += "\n"

    # Financial Details
    result += "### Financial Summary\n"
    fd = invoice.financial_details
    if fd.currency:
        result += f"- **Currency:** {fd.currency}\n"
    result += f"- **Subtotal:** {fd.subtotal}\n"
    result += f"- **Tax ({fd.tax.type}):** {fd.tax.amount} ({fd.tax.rate}%)\n"
    result += f"- **Total:** {fd.total_amount}\n"
    if fd.payment and fd.payment.method:
        result += f"- **Payment Method:** {fd.payment.method.value}\n"
    result += "\n"

    # Line Items
    if invoice.items:
        result += "### Line Items\n"
        for i, item in enumerate(invoice.items, 1):
            result += f"\n**Item {i}**\n"
            if item.item_id:
                result += f"- ID: {item.item_id}\n"
            if item.description:
                result += f"- Description: {item.description}\n"
            result += f"- Quantity: {item.quantity}\n"
            result += f"- Unit Price: {item.unit_price}\n"
            result += f"- Total: {item.line_total}\n"

    return result


async def process_invoice(file, token: str | None = None, processing_mode: str = "fast") -> tuple[str, str, str, str]:
    """
    Process uploaded invoice file with selectable processing mode.

    Args:
        file: Uploaded PDF file
        token: API authentication token
        processing_mode: "fast" (no preprocessing) or "enhanced" (with preprocessing)

    Returns:
        Tuple of (result_text, metadata_text, json_data, status_message)
    """
    if not file:
        return "", "", "", "Please upload a PDF file"

    if not token:
        return "", "", "", "Please enter your API token"

    try:
        # Clean and validate token
        token = token.strip()
        if not token:
            return "", "", "", "Please enter a valid API token"

        # Validate token format (should have 3 parts separated by dots)
        token_parts = token.split('.')
        if len(token_parts) != 3:
            return "", "", "", f"Invalid token format. Token has {len(token_parts)} parts, expected 3"

        jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

        # Read file
        start_time = time.perf_counter()
        file_bytes = file

        # Calculate hash
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        # Check cache
        cached_invoice = await cache_service.get_invoice(file_hash)

        if cached_invoice:
            invoice_result = cached_invoice
            from_cache = True
            cache_status = "Cached"
        else:
            # Classify document
            logger.info("Classifying document...")
            classification_result = await document_classifier.classify_bytes(file_bytes)

            if not classification_result.is_invoice:
                return (
                    "",
                    f"**Document Type:** {classification_result.document_type}\n"
                    f"**Reason:** {classification_result.reason}",
                    "",
                    f"Document is not an invoice ({classification_result.document_type})"
                )

            # Parse invoice with selected mode
            if processing_mode == "lightning":
                logger.info("⚡ Parsing invoice with LIGHTNING mode...")
                from app.services.parser.ultra_fast_parser import ultra_fast_parser
                invoice_result, validation_info = await ultra_fast_parser.parse_bytes_ultra_fast(file_bytes)
                processing_method = "⚡ Lightning (ultra-fast)"
            elif processing_mode == "enhanced":
                logger.info("Parsing invoice with enhanced preprocessing...")
                from app.services.parser.parser import enhanced_invoice_parser
                invoice_result, validation_info = await enhanced_invoice_parser.parse_bytes(file_bytes, use_preprocessing=True)
                processing_method = "Enhanced (with preprocessing)"
            else:
                logger.info("Parsing invoice with fast mode...")
                from app.services.parser.ultra_fast_parser import ultra_fast_parser
                invoice_result, validation_info = await ultra_fast_parser.parse_bytes_ultra_fast(file_bytes)
                processing_method = "Fast (direct processing)"

            from_cache = False
            cache_status = "Fresh"

            # Cache result
            await cache_service.set_invoice(file_hash, invoice_result)

        end_time = time.perf_counter()
        processing_time = end_time - start_time

        # Format results
        formatted_result = format_invoice_result(invoice_result)

        # Add processing method info if not from cache
        method_info = ""
        if not from_cache:
            method_info = f"- **Processing Method:** {processing_method}\n"
            if 'validation_info' in locals() and validation_info:
                quality_score = validation_info.get('validation_results', {}).get('quality_score', 'N/A')
                method_info += f"- **Quality Score:** {quality_score}\n"

        metadata = f"""### Processing Information
- **File Hash:** `{file_hash[:16]}...`
- **Processing Time:** {processing_time:.2f}s
- **Cache Status:** {cache_status}
- **From Cache:** {'Yes' if from_cache else 'No'}
{method_info}"""

        # JSON output
        json_output = json.dumps(invoice_result.model_dump(), indent=2, default=str)

        return (
            formatted_result,
            metadata,
            json_output,
            f"Invoice processed successfully in {processing_time:.2f}s"
        )

    except Exception as e:
        logger.exception(f"Error processing invoice: {e}")
        return "", "", "", f"Error: {str(e)}"


def create_gradio_interface():
    """Create the Gradio interface for invoice parsing."""

    with gr.Blocks(title="Invoice Parser UI", theme=gr.themes.Default()) as demo:
        gr.Markdown(
            """
            # Invoice Parser UI

            Upload a PDF invoice to extract structured data using AI.

            **Choose your processing mode:**
            - **⚡ Lightning Mode**: Ultra-fast processing (~1-1.5 seconds) - Maximum speed with aggressive optimizations
            - **🚀 Fast Mode**: Direct processing (~2-3 seconds) - Recommended for most invoices
            - **🔍 Enhanced Mode**: With image preprocessing (~6-8 seconds) - For low-quality scanned documents

            **Authentication Required**: Enter your API token to access the service.
            """
        )

        with gr.Row():
            with gr.Column(scale=2):
                # Token input with persistence
                token_input = gr.Textbox(
                    label="API Token",
                    placeholder="Enter your JWT token here (eyJ...)",
                    type="text",
                    value="",
                    info="Your authentication token for API access",
                    lines=3,
                    max_lines=3
                )

                # File upload
                file_input = gr.File(
                    label="Upload Invoice (PDF)",
                    file_types=[".pdf"],
                    type="binary"
                )

                # Processing mode selection
                processing_mode = gr.Radio(
                    choices=[
                        ("⚡ Lightning Mode (<1.5s)", "lightning"),
                        ("🚀 Fast Mode (2-3s)", "fast"),
                        ("🔍 Enhanced Mode (6-8s)", "enhanced")
                    ],
                    value="lightning",
                    label="Processing Mode",
                    info="Lightning: Ultra-fast | Fast: Direct processing | Enhanced: With preprocessing"
                )

                # Process button
                process_btn = gr.Button(
                    "Process Invoice",
                    variant="primary",
                    size="lg"
                )

                # Status message
                status_output = gr.Textbox(
                    label="Status",
                    interactive=False,
                    lines=1
                )

            with gr.Column(scale=3):
                # Results tabs
                with gr.Tabs():
                    with gr.Tab("Parsed Data"):
                        result_output = gr.Markdown(
                            value="*Upload an invoice to see results*"
                        )

                    with gr.Tab("Metadata"):
                        metadata_output = gr.Markdown(
                            value="*Processing information will appear here*"
                        )

                    with gr.Tab("JSON Output"):
                        json_output = gr.Code(
                            language="json",
                            label="Raw JSON Data",
                            interactive=False
                        )

        # Example and instructions
        with gr.Accordion("Instructions & Examples", open=False):
            gr.Markdown(
                """
                ### How to use:
                1. **Get a token**: Generate a JWT token the CLI utility
                2. **Enter token**: Paste your token in the 'API Token' field
                3. **Upload invoice**: Select a PDF invoice file
                4. **Process**: Click the Process Invoice button
                5. **View results**: Check the parsed data, metadata, and JSON output
                ```
                """
            )

        # Connect the process button
        process_btn.click(
            fn=process_invoice,
            inputs=[file_input, token_input, processing_mode],
            outputs=[result_output, metadata_output, json_output, status_output]
        )

        # Auto-save token to browser storage (for convenience)
        demo.load(
            None,
            None,
            None,
            js="""
            () => {
                // Try to load saved token
                const savedToken = localStorage.getItem('invoice_parser_token');
                if (savedToken) {
                    document.querySelector('input[type="password"]').value = savedToken;
                }

                // Save token when it changes
                document.querySelector('input[type="password"]').addEventListener('change', (e) => {
                    localStorage.setItem('invoice_parser_token', e.target.value);
                });
            }
            """
        )

    return demo
