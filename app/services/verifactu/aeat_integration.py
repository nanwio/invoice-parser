# Copyright 2024 Artificial Intelligence Labs, SL

import asyncio
import aiohttp
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from loguru import logger

from app.services.verifactu.models import AEATValidationResult
from app.services.cache import cache_service


class AEATIntegration:
    """
    Real-time AEAT (Spanish Tax Agency) Integration for VERIFACTU validation.

    Provides connectivity with official AEAT systems to validate:
    - Invoice existence in VERIFACTU system
    - Issuer registration status
    - Real-time compliance verification
    """

    def __init__(self):
        # AEAT VERIFACTU API endpoints (official URLs)
        self.aeat_endpoints = {
            'verify_invoice': 'https://sede.agenciatributaria.gob.es/Sede/verificafactura',
            'check_issuer': 'https://www2.agenciatributaria.gob.es/wlpl/BUCV-JDIT/ConsultaEmisores',
            'verifactu_status': 'https://sede.agenciatributaria.gob.es/Sede/procedimientoini/G322.shtml'
        }

        # Cache configuration for AEAT responses
        self.cache_ttl = {
            'invoice_verification': 3600,  # 1 hour
            'issuer_status': 7200,  # 2 hours
            'issuer_registration': 86400  # 24 hours
        }

        # Request timeouts
        self.request_timeout = 30  # seconds

    async def validate_invoice_with_aeat(
        self,
        nif: str,
        invoice_number: str,
        issue_date: str,
        total_amount: float
    ) -> AEATValidationResult:
        """
        Validate invoice existence and data with AEAT VERIFACTU system.

        Args:
            nif: Issuer's tax ID
            invoice_number: Invoice number
            issue_date: Invoice issue date
            total_amount: Total invoice amount

        Returns:
            AEATValidationResult with validation status
        """
        logger.info(f"Validating invoice {invoice_number} with AEAT")

        # Create cache key for this validation
        cache_key = f"aeat_validation:{nif}:{invoice_number}:{issue_date}:{total_amount}"

        try:
            # Check cache first
            cached_result = await self._get_cached_validation(cache_key)
            if cached_result:
                logger.info("AEAT validation result from cache")
                return cached_result

            # Perform real-time validation
            result = await self._perform_aeat_validation(nif, invoice_number, issue_date, total_amount)

            # Cache the result
            await self._cache_validation_result(cache_key, result)

            return result

        except Exception as e:
            logger.error(f"Error validating with AEAT: {e}")
            return AEATValidationResult(
                invoice_exists=False,
                issuer_registered=False,
                issuer_active=False,
                validation_timestamp=datetime.now().isoformat(),
                aeat_response_code="ERROR",
                cache_hit=False
            )

    async def check_issuer_verifactu_status(self, nif: str) -> Dict[str, Any]:
        """
        Check if issuer is registered and active in VERIFACTU system.

        Args:
            nif: Issuer's tax ID

        Returns:
            Dictionary with issuer status information
        """
        logger.info(f"Checking VERIFACTU status for issuer {nif}")

        cache_key = f"issuer_status:{nif}"

        try:
            # Check cache first
            cached_status = await self._get_cached_issuer_status(cache_key)
            if cached_status:
                logger.info("Issuer status from cache")
                return cached_status

            # Query AEAT for issuer status
            status = await self._query_issuer_status(nif)

            # Cache the result
            await self._cache_issuer_status(cache_key, status)

            return status

        except Exception as e:
            logger.error(f"Error checking issuer status: {e}")
            return {
                'registered': False,
                'active': False,
                'registration_date': None,
                'error': str(e)
            }

    async def _perform_aeat_validation(
        self,
        nif: str,
        invoice_number: str,
        issue_date: str,
        total_amount: float
    ) -> AEATValidationResult:
        """Perform the actual AEAT validation request."""

        try:
            # Prepare validation parameters
            validation_params = {
                'nif': nif,
                'num': invoice_number,
                'fecha': issue_date,
                'importe': f"{total_amount:.2f}"
            }

            # Make request to AEAT verification endpoint
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.request_timeout)) as session:
                response_data = await self._make_aeat_request(
                    session,
                    self.aeat_endpoints['verify_invoice'],
                    validation_params
                )

            # Parse AEAT response
            validation_result = self._parse_aeat_response(response_data)

            # Also check issuer status
            issuer_status = await self.check_issuer_verifactu_status(nif)

            return AEATValidationResult(
                invoice_exists=validation_result.get('invoice_exists', False),
                issuer_registered=issuer_status.get('registered', False),
                issuer_active=issuer_status.get('active', False),
                validation_timestamp=datetime.now().isoformat(),
                aeat_response_code=validation_result.get('response_code'),
                cache_hit=False
            )

        except Exception as e:
            logger.error(f"AEAT validation request failed: {e}")
            raise

    async def _make_aeat_request(
        self,
        session: aiohttp.ClientSession,
        endpoint: str,
        params: Dict[str, str]
    ) -> Dict[str, Any]:
        """Make HTTP request to AEAT endpoint."""

        try:
            # AEAT requires specific headers
            headers = {
                'User-Agent': 'VERIFACTU-Validator/1.0',
                'Accept': 'text/html,application/json',
                'Accept-Language': 'es-ES,es;q=0.9'
            }

            # Make GET request with parameters
            async with session.get(endpoint, params=params, headers=headers) as response:
                logger.debug(f"AEAT request: {response.url}")

                if response.status == 200:
                    # Try to parse as JSON first, then as HTML
                    content_type = response.headers.get('content-type', '')

                    if 'application/json' in content_type:
                        data = await response.json()
                    else:
                        text = await response.text()
                        data = self._parse_html_response(text)

                    return {
                        'status_code': response.status,
                        'data': data,
                        'success': True
                    }
                else:
                    logger.warning(f"AEAT request failed with status {response.status}")
                    return {
                        'status_code': response.status,
                        'data': None,
                        'success': False,
                        'error': f"HTTP {response.status}"
                    }

        except asyncio.TimeoutError:
            logger.error("AEAT request timeout")
            raise Exception("Timeout connecting to AEAT")

        except Exception as e:
            logger.error(f"AEAT request error: {e}")
            raise

    def _parse_html_response(self, html_content: str) -> Dict[str, Any]:
        """Parse HTML response from AEAT (when JSON not available)."""
        try:
            # Look for specific indicators in HTML response
            indicators = {
                'invoice_found': [
                    'factura verificada',
                    'factura válida',
                    'invoice verified',
                    'datos correctos'
                ],
                'invoice_not_found': [
                    'factura no encontrada',
                    'no se ha encontrado',
                    'invoice not found',
                    'datos incorrectos'
                ],
                'issuer_valid': [
                    'emisor válido',
                    'emisor registrado',
                    'valid issuer'
                ],
                'system_error': [
                    'error del sistema',
                    'servicio no disponible',
                    'system error',
                    'service unavailable'
                ]
            }

            html_lower = html_content.lower()

            # Check for various indicators
            invoice_found = any(indicator in html_lower for indicator in indicators['invoice_found'])
            invoice_not_found = any(indicator in html_lower for indicator in indicators['invoice_not_found'])
            issuer_valid = any(indicator in html_lower for indicator in indicators['issuer_valid'])
            system_error = any(indicator in html_lower for indicator in indicators['system_error'])

            return {
                'invoice_found': invoice_found,
                'invoice_not_found': invoice_not_found,
                'issuer_valid': issuer_valid,
                'system_error': system_error,
                'raw_html': html_content[:500]  # First 500 chars for debugging
            }

        except Exception as e:
            logger.error(f"Error parsing HTML response: {e}")
            return {'parse_error': str(e)}

    def _parse_aeat_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse AEAT response and extract validation results."""
        try:
            if not response_data.get('success'):
                return {
                    'invoice_exists': False,
                    'response_code': 'REQUEST_FAILED',
                    'error': response_data.get('error')
                }

            data = response_data.get('data', {})

            # Handle JSON response
            if isinstance(data, dict) and 'status' in data:
                return {
                    'invoice_exists': data.get('status') == 'valid',
                    'response_code': data.get('code', 'UNKNOWN'),
                    'details': data.get('details')
                }

            # Handle HTML response
            elif isinstance(data, dict) and 'invoice_found' in data:
                if data.get('system_error'):
                    return {
                        'invoice_exists': False,
                        'response_code': 'SYSTEM_ERROR',
                        'error': 'AEAT system temporarily unavailable'
                    }

                return {
                    'invoice_exists': data.get('invoice_found', False) and not data.get('invoice_not_found', False),
                    'response_code': 'HTML_PARSED',
                    'issuer_valid': data.get('issuer_valid', False)
                }

            else:
                return {
                    'invoice_exists': False,
                    'response_code': 'UNKNOWN_RESPONSE',
                    'error': 'Unable to parse AEAT response'
                }

        except Exception as e:
            logger.error(f"Error parsing AEAT response: {e}")
            return {
                'invoice_exists': False,
                'response_code': 'PARSE_ERROR',
                'error': str(e)
            }

    async def _query_issuer_status(self, nif: str) -> Dict[str, Any]:
        """Query AEAT for issuer registration status."""
        try:
            params = {'nif': nif}

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.request_timeout)) as session:
                response_data = await self._make_aeat_request(
                    session,
                    self.aeat_endpoints['check_issuer'],
                    params
                )

            # Parse issuer status response
            if response_data.get('success'):
                data = response_data.get('data', {})

                # Look for registration indicators
                registered = False
                active = False
                registration_date = None

                if isinstance(data, dict):
                    if 'status' in data:
                        registered = data.get('status') in ['registered', 'active']
                        active = data.get('status') == 'active'
                    elif 'registered' in data:
                        registered = data.get('registered', False)
                        active = data.get('active', False)
                else:
                    # Parse HTML for indicators
                    html_content = str(data)
                    registered = any(indicator in html_content.lower() for indicator in [
                        'emisor registrado', 'issuer registered', 'alta en verifactu'
                    ])
                    active = any(indicator in html_content.lower() for indicator in [
                        'emisor activo', 'issuer active', 'estado activo'
                    ])

                return {
                    'registered': registered,
                    'active': active,
                    'registration_date': registration_date,
                    'query_timestamp': datetime.now().isoformat()
                }

            else:
                return {
                    'registered': False,
                    'active': False,
                    'registration_date': None,
                    'error': response_data.get('error', 'Query failed')
                }

        except Exception as e:
            logger.error(f"Error querying issuer status: {e}")
            return {
                'registered': False,
                'active': False,
                'registration_date': None,
                'error': str(e)
            }

    async def _get_cached_validation(self, cache_key: str) -> Optional[AEATValidationResult]:
        """Get cached AEAT validation result."""
        try:
            cached_data = await cache_service.get(cache_key)
            if cached_data:
                # Add cache hit indicator
                cached_data['cache_hit'] = True
                return AEATValidationResult(**cached_data)
        except Exception as e:
            logger.warning(f"Error retrieving cached validation: {e}")
        return None

    async def _cache_validation_result(self, cache_key: str, result: AEATValidationResult):
        """Cache AEAT validation result."""
        try:
            # Convert to dict and remove cache_hit flag for storage
            result_dict = result.model_dump()
            result_dict.pop('cache_hit', None)

            await cache_service.set(
                cache_key,
                result_dict,
                ttl=self.cache_ttl['invoice_verification']
            )
        except Exception as e:
            logger.warning(f"Error caching validation result: {e}")

    async def _get_cached_issuer_status(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached issuer status."""
        try:
            return await cache_service.get(cache_key)
        except Exception as e:
            logger.warning(f"Error retrieving cached issuer status: {e}")
        return None

    async def _cache_issuer_status(self, cache_key: str, status: Dict[str, Any]):
        """Cache issuer status."""
        try:
            await cache_service.set(
                cache_key,
                status,
                ttl=self.cache_ttl['issuer_status']
            )
        except Exception as e:
            logger.warning(f"Error caching issuer status: {e}")

    async def get_aeat_system_status(self) -> Dict[str, Any]:
        """Check if AEAT services are available."""
        try:
            status_results = {}

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                # Test each endpoint
                for service, endpoint in self.aeat_endpoints.items():
                    try:
                        async with session.head(endpoint) as response:
                            status_results[service] = {
                                'available': response.status < 500,
                                'status_code': response.status,
                                'response_time': None  # Could measure this
                            }
                    except Exception as e:
                        status_results[service] = {
                            'available': False,
                            'status_code': None,
                            'error': str(e)
                        }

            # Overall system status
            all_available = all(result.get('available', False) for result in status_results.values())

            return {
                'overall_status': 'available' if all_available else 'degraded',
                'services': status_results,
                'checked_at': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error checking AEAT system status: {e}")
            return {
                'overall_status': 'unknown',
                'error': str(e),
                'checked_at': datetime.now().isoformat()
            }