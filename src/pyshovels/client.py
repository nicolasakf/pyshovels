import logging
import traceback
import requests
import pandas as pd
import datetime
from typing import Iterable, List
from pathlib import Path
import os

__all__ = [
    "US_STATES", 
    "load_env",
    "ShovelsAPI",
]

US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
]

def elapsed_time_str(elapsed_seconds: float) -> str:
    """
    Converts a number of seconds into a string of hours, minutes, and seconds.

    Args:
        elapsed_seconds (float): The number of seconds to convert.

    Returns:
        str: The string of hours, minutes, and seconds.
    """
    hours = elapsed_seconds // (60**2)
    left = elapsed_seconds % (60**2)
    minutes = left // 60
    seconds = elapsed_seconds % 60
    hours_str = f'{hours:.0f}h ' if hours > 0 else ''
    minutes_str = f'{minutes:.0f}min ' if minutes > 0 else ''
    seconds_str = f'{seconds:.1f}s' if seconds > 0 else ''
    return (hours_str + minutes_str + seconds_str).strip()

def load_env(env_name: str | None = None, env_path: str | None = None):
    """
    Loads environment variables from a .env file.
    """
    from dotenv import load_dotenv
    if env_path:
        _env_path = env_path
    else:
        env_filename = f'.env.{env_name}' if env_name else '.env'
        _env_path = Path(__file__).parent.parent.parent / env_filename
    assert _env_path.exists(), f"Environment file {_env_path} does not exist"
    load_dotenv(_env_path)

class ShovelsAPI:
    """
    Shovels API client.
    Full documentation: https://docs.shovels.ai/api-reference/
    """
    BASE_URL = "https://api.shovels.ai/v2"

    def __init__(self, api_key: str | None = None, base_url: str | None = None, logger: logging.Logger | None = None):
        """Initialize the Shovels API client.

        Parameters
        ----------
        api_key : str, optional
            API key for the Shovels API. If not provided, it attempts to
            retrieve it from the `SHOVELS_API_KEY` environment variable.
        base_url : str, optional
            Base URL for the Shovels API. If not provided, it attempts to
            retrieve it from the `SHOVELS_API_URL` environment variable.
        logger : logging.Logger, optional
            A logger instance for logging messages. If not provided, a default
            logger named after the module (`__name__`) will be used.
        """
        self.session: requests.Session = requests.Session()
        self.session.headers['X-API-Key'] = api_key or os.getenv('SHOVELS_API_KEY')
        self.base_url: str = base_url or os.getenv('SHOVELS_API_URL') or self.BASE_URL
        self.logger: logging.Logger = logger or logging.getLogger(__name__)

    def _make_request(self, url: str, params: dict | None = None) -> dict:
        """Make an HTTP GET request to the Shovels API.

        Parameters
        ----------
        url : str
            The URL to make the request to.
        params : dict, optional
            The parameters to pass to the request. Default is None.

        Returns
        -------
        dict
            The JSON response from the Shovels API as a dictionary.
        """
        response = self.session.get(url, params=params)
        if response.status_code != 200:
            self.logger.error(f"Error fetching {url}: HTTP Error {response.status_code}: {response.text}")
            return
        result = response.json()
        self.logger.debug(f"Number of items returned: {result.get('size', 0)}")
        return result
    
    def _make_paginated_request(
        self,
        url: str,
        params: dict | None = None,
        page: int | None = None,
        size: int | None = None,
        cursor: str | None = None,
        max_iterations: int | None = None
    ) -> List[dict]:
        """Make a paginated request to the Shovels API.

        This method handles both cursor-based and page-based pagination.

        Parameters
        ----------
        url : str
            The URL to make the request to.
        params : dict, optional
            The parameters to pass to the request. Default is None.
        page : int, optional
            The page number to fetch for offset-based pagination. Default is None.
        size : int, optional
            The number of items to fetch per page. Default is None. Min is 1, Max is 100.
        cursor : str, optional
            The cursor to fetch the next page for cursor-based pagination.
            Default is None.
        max_iterations : int, optional
            The maximum number of pages/iterations to fetch. If None, fetches all
            available data. Default is None.

        Returns
        -------
        List[dict]
            A list of all items fetched from the Shovels API across pages.
        """
        results: List[dict] = []
        i = 0
        _params = {**params} if params else {}
        self.logger.info(f"Request params: {_params}" if _params else "No params")
        while True:
            try:
                i += 1
                if cursor:
                    _params["cursor"] = cursor
                if page:
                    _params["page"] = page
                if size:
                    _params["size"] = size

                self.logger.debug(f"Iteration {i}: Page {page}, Cursor {cursor}, Size {size}")
                content = self._make_request(url, _params)
                if content is None:
                    break
                results.extend(content["items"])
                if max_iterations is not None and i == max_iterations:
                    break
                if 'next_cursor' in content:
                    if content["next_cursor"] is None:
                        break
                    cursor = content["next_cursor"]
                elif 'next_page' in content:
                    if content["next_page"] is None:
                        break
                    page = content["next_page"]
                else:
                    break
            except Exception:
                stack_trace = traceback.format_exc()
                idx_str = f"cursor {cursor}" if cursor else f"page {page}"
                self.logger.error(f"Error fetching {idx_str}")
                self.logger.error(stack_trace)
                break
        return results

    # region: location & residents
    def search_location(self, query: str, level: str) -> List[dict]:
        """Fetch location basic info for a given location query.

        This method aggregates the following endpoints:
        - https://docs.shovels.ai/api-reference/states/search-states
        - https://docs.shovels.ai/api-reference/zipcodes/search-zipcodes
        - https://docs.shovels.ai/api-reference/jurisdictions/search-jurisdictions
        - https://docs.shovels.ai/api-reference/counties/search-counties
        - https://docs.shovels.ai/api-reference/cities/search-cities
        - https://docs.shovels.ai/api-reference/addresses/search-addresses

        Parameters
        ----------
        query : str
            The text to search for in the location fields.
        level : str
            The level of the location to search.
            Options: "states", "zipcodes", "jurisdictions", "counties", "cities", "addresses".

        Returns
        -------
        List[dict]
            A list of locations matching the query. Returns an empty list if
            no matches are found or an error occurs.
        """
        url = f"{self.base_url}/{level}/search"
        params = {"q": query}
        content = self._make_request(url, params)
        return content.get("items", [])

    def get_location_monthly_metrics(
        self,
        geo_ids: List[str],
        level: str,
        params: dict | None = None,
        **kwargs
    ) -> pd.DataFrame:
        """Get monthly metrics for specific locations by their Geo IDs.

        This method aggregates the following endpoints:
        - https://docs.shovels.ai/api-reference/jurisdictions/get-jurisdiction-monthly-metrics
        - https://docs.shovels.ai/api-reference/counties/get-county-monthly-metrics
        - https://docs.shovels.ai/api-reference/cities/get-city-monthly-metrics
        - https://docs.shovels.ai/api-reference/addresses/get-address-monthly-metrics

        Parameters
        ----------
        geo_ids : List[str]
            A list of Geo IDs for which to retrieve monthly metrics.
        level : str
            The geographical level of the `geo_ids`.
            Examples: "jurisdictions", "cities", "counties", "states", "zipcodes".
        params : dict, optional
            A dictionary of parameters to filter the metrics (e.g., date ranges).
            Default is None.
        **kwargs : dict, optional
            Keyword arguments passed to the `_make_paginated_request` method.

        Returns
        -------
        pd.DataFrame
            A DataFrame containing the monthly metrics for the specified
            locations.
        """
        results: List[dict] = []
        self.logger.info('--------------------------------')
        self.logger.info(f"Fetching monthly metrics for {len(geo_ids)} geo IDs: {geo_ids}")
        for i, geo_id in enumerate(geo_ids):
            url = f"{self.base_url}/{level}/{geo_id}/metrics/monthly"
            self.logger.info(f"Fetching monthly metrics for geo ID: {geo_id} ({i+1}/{len(geo_ids)})")
            try:
                results.extend(self._make_paginated_request(url, params, **kwargs))
            except Exception:
                stack_trace = traceback.format_exc()
                self.logger.error(f"Error fetching monthly metrics for location ID: {geo_id}")
                self.logger.error(stack_trace)
                continue
        self.logger.info('--------------------------------')
        return pd.DataFrame(results)

    def get_location_current_metrics(
        self,
        geo_ids: List[str],
        level: str,
        params: dict | None = None,
        **kwargs
    ) -> pd.DataFrame:
        """Get current metrics for specific locations by their Geo IDs.

        This method aggregates the following endpoints:
        - https://docs.shovels.ai/api-reference/jurisdictions/get-jurisdiction-current-metrics
        - https://docs.shovels.ai/api-reference/counties/get-county-current-metrics
        - https://docs.shovels.ai/api-reference/cities/get-city-current-metrics
        - https://docs.shovels.ai/api-reference/addresses/get-address-current-metrics

        Parameters
        ----------
        geo_ids : List[str]
            A list of Geo IDs for which to retrieve current metrics.
        level : str
            The geographical level of the `geo_ids`.
                Options: "jurisdictions", "cities", "counties", "addresses".
        params : dict, optional
            A dictionary of parameters to filter the metrics. Default is None.
        **kwargs : dict, optional
            Keyword arguments passed to the `_make_paginated_request` method.

        Returns
        -------
        pd.DataFrame
            A DataFrame containing the current metrics for the specified
            locations.
        """
        results: List[dict] = []
        self.logger.info('--------------------------------')
        self.logger.info(f"Fetching current metrics for {len(geo_ids)} geo IDs: {geo_ids}")
        for i, geo_id in enumerate(geo_ids):
            url = f"{self.base_url}/{level}/{geo_id}/metrics/current"
            self.logger.info(f"Fetching current metrics for geo ID: {geo_id} ({i+1}/{len(geo_ids)})")
            try:
                results.extend(self._make_paginated_request(url, params, **kwargs))
            except Exception:
                stack_trace = traceback.format_exc()
                self.logger.error(f"Error fetching current metrics for geo ID: {geo_id}")
                self.logger.error(stack_trace)
                continue
        self.logger.info('--------------------------------')
        return pd.DataFrame(results)

    def get_location_details(
        self,
        geo_ids: List[str],
        level: str,
        **kwargs
    ) -> List[dict]:
        """Get details for a specific location by its Geo ID.

        This method aggregates the following endpoints:
        - https://docs.shovels.ai/api-reference/jurisdictions/get-jurisdiction-details
        - https://docs.shovels.ai/api-reference/counties/get-county-details
        - https://docs.shovels.ai/api-reference/cities/get-city-details

        Note: For "addresses" level, use the `get_residents` method instead.

        Parameters
        ----------
        geo_ids : List[str]
            A list of Geo IDs for which to retrieve details.
        level : str
            The geographical level of the `geo_ids`.
            Options: "jurisdictions", "counties", "cities".
        **kwargs : dict, optional
            Keyword arguments passed to the `_make_paginated_request` method.

        Returns
        -------
        List[dict]
            A list of dictionaries containing the location details.
        """
        assert level != 'addresses', 'For addresses, use the get_residents method.'
        results: List[dict] = []
        self.logger.info('--------------------------------')
        self.logger.info(f"Fetching details for {len(geo_ids)} geo IDs: {geo_ids}")
        url = f"{self.base_url}/{level}"
        for i, geo_id in enumerate(geo_ids):
            self.logger.info(f"Fetching details for geo ID: {geo_id} ({i+1}/{len(geo_ids)})")
            try:
                results.extend(self._make_paginated_request(url, {"geo_id": geo_id}, **kwargs))
            except Exception:
                stack_trace = traceback.format_exc()
                self.logger.error(f"Error fetching details for geo ID: {geo_id}")
                self.logger.error(stack_trace)
                continue
        self.logger.info('--------------------------------')
        return results

    def get_residents(
        self,
        geo_ids: Iterable[str],
        **kwargs
    ) -> pd.DataFrame:
        """Fetch residents for given geographical IDs (typically address IDs).

        Refer to the official Shovels API documentation for detailed
        parameter options:
        https://docs.shovels.ai/api-reference/addresses/get-residents

        Parameters
        ----------
        geo_ids : Iterable[str]
            An iterable of Geo IDs (address-level IDs) to fetch residents for.
        **kwargs : dict, optional
            Keyword arguments passed to the `_make_paginated_request` method.

        Returns
        -------
        pd.DataFrame
            A DataFrame containing resident data for all specified geo_ids.
        """
        results: List[dict] = []
        self.logger.info('--------------------------------')
        self.logger.info(f'Starting to fetch residents for {len(geo_ids)} geo_ids')
        for i, geo_id in enumerate(geo_ids):
            url = f"{self.base_url}/addresses/{geo_id}/residents"
            self.logger.info(f'Fetching residents for geo_id: {geo_id} ({i+1}/{len(geo_ids)})')
            try:
                results.extend(self._make_paginated_request(url, None, **kwargs))
            except Exception:
                stack_trace = traceback.format_exc()
                self.logger.error(f"Failed to fetch residents for geo_id: {geo_id}")
                self.logger.error(stack_trace)
                continue
        self.logger.info('--------------------------------')
        return pd.DataFrame(results)
    # endregion: location & residents

    # region: contractor
    def search_contractors(
        self,
        params: dict | None = None,
        geo_ids: Iterable[str] | str | None = None,
        **kwargs
    ) -> pd.DataFrame:
        """Search for contractors based on specified criteria.

        Refer to the official Shovels API documentation for detailed
        parameter options: https://docs.shovels.ai/api-reference/contractors/search-contractors

        Parameters
        ----------
        params : dict
            A dictionary of parameters for the search. This typically includes
            filters like `permit_from`, `permit_to`, `tag_id`, etc.
            The `permit_from` and `permit_to` fields will default to the last
            180 days and today respectively if not provided.
        geo_ids : Iterable[str] or str, optional
            A single Geo ID (string) or an iterable of Geo IDs to search within.
            If None, the search will be performed across all US states (defined
            in `US_STATES`). Default is None.
        **kwargs : dict, optional
            Keyword arguments passed to the `_make_paginated_request` method.

        Returns
        -------
        pd.DataFrame
            A DataFrame containing the search results with contractor data.
            An empty DataFrame is returned if no contractors are found or
            an error occurs during the process for all geo_ids.
        """
        url = f"{self.base_url}/contractors/search"
        if geo_ids is None:
            geo_ids = US_STATES
        if isinstance(geo_ids, str):
            geo_ids = [geo_ids]
        _params = {**params} if params else {}
        _params["permit_from"] = _params.get("permit_from") or (datetime.date.today() - datetime.timedelta(days=180)).strftime("%Y-%m-%d")
        _params["permit_to"] = _params.get("permit_to") or datetime.date.today().strftime("%Y-%m-%d")
        self.logger.info('--------------------------------')
        self.logger.info(f"Fetching contractors for {len(geo_ids)} geo_ids: {geo_ids}")
        results: List[dict] = []
        for i, geo_id in enumerate(geo_ids):
            self.logger.info(f"Fetching contractors for geo_id: {geo_id} ({i+1}/{len(geo_ids)})")
            try:
                _params["geo_id"] = geo_id
                results.extend(self._make_paginated_request(url, _params, **kwargs))
            except Exception:
                stack_trace = traceback.format_exc()
                self.logger.error(f"Error fetching geo_id {geo_id}")
                self.logger.error(stack_trace)
                continue
        self.logger.info('--------------------------------')
        return pd.DataFrame(results)
    
    def get_contractors_by_id(
        self,
        contractor_ids: List[str],
        **kwargs
    ) -> pd.DataFrame:
        """Retrieve detailed information for specific contractors by their IDs.

        Refer to the official Shovels API documentation for detailed
        parameter options:
        https://docs.shovels.ai/api-reference/contractors/get-contractors-by-id

        Parameters
        ----------
        contractor_ids : List[str]
            A list of contractor IDs to fetch.
        **kwargs : dict, optional
            Keyword arguments passed to the `_make_paginated_request` method.

        Returns
        -------
        pd.DataFrame
            A DataFrame containing the data for the specified contractor IDs.
        """
        url = f"{self.base_url}/contractors"
        params = {"ids": contractor_ids}
        content = self._make_paginated_request(url, params, **kwargs)
        return pd.DataFrame(content)

    def get_permits_by_contractor_id(
        self,
        contractor_ids: Iterable[str],
        **kwargs
    ) -> pd.DataFrame:
        """Fetch permits associated with given contractor IDs.

        Refer to the official Shovels API documentation for detailed
        parameter options:
        https://docs.shovels.ai/api-reference/contractors/get-permits-by-contractor-id

        Parameters
        ----------
        contractor_ids : Iterable[str]
            An iterable of contractor IDs for which to fetch permits.
        **kwargs : dict, optional
            Keyword arguments passed to the `_make_paginated_request` method.

        Returns
        -------
        pd.DataFrame
            A DataFrame containing permit data for all specified contractor IDs.
        """
        results: List[dict] = []
        self.logger.info('--------------------------------')
        self.logger.info(f'Starting to fetch permits for {len(contractor_ids)} contractors')
        for i, cid in enumerate(contractor_ids):
            url = f"{self.base_url}/contractors/{cid}/permits"
            self.logger.info(f'Fetching permits for contractor ID: {cid} ({i+1}/{len(contractor_ids)})')
            try:
                results.extend(self._make_paginated_request(url, None, **kwargs))
            except Exception as e:
                stack_trace = traceback.format_exc()
                self.logger.error(f"Failed to fetch permits for contractor ID: {cid}")
                self.logger.error(stack_trace)
                continue
        self.logger.info('--------------------------------')
        return pd.DataFrame(results)
    
    def get_filtered_metrics_by_contractor_id(
        self,
        contractor_ids: List[str],
        params: dict | None = None,
        **kwargs
    ) -> pd.DataFrame:
        """Get filtered metrics for specific contractors by their IDs.

        Refer to the official Shovels API documentation for detailed
        parameter options:
        https://docs.shovels.ai/api-reference/contractors/get-filtered-metrics-by-contractor-id

        Parameters
        ----------
        contractor_ids : List[str]
            A list of contractor IDs for which to retrieve metrics.
        params : dict, optional
            A dictionary of parameters to filter the metrics (e.g., date ranges,
            permit types). Default is None.
        **kwargs : dict, optional
            Keyword arguments passed to the `_make_paginated_request` method.

        Returns
        -------
        pd.DataFrame
            A DataFrame containing the filtered metrics for the specified
            contractor IDs.
        """
        results: List[dict] = []
        self.logger.info('--------------------------------')
        self.logger.info(f"Fetching metrics for {len(contractor_ids)} contractor IDs: {contractor_ids}")
        for i, contractor_id in enumerate(contractor_ids):
            url = f"{self.base_url}/contractors/{contractor_id}/metrics"
            self.logger.info(f"Fetching metrics for contractor ID: {contractor_id} ({i+1}/{len(contractor_ids)})")
            try:
                results.extend(self._make_paginated_request(url, params, **kwargs))
            except Exception:
                stack_trace = traceback.format_exc()
                self.logger.error(f"Error fetching metrics for contractor ID: {contractor_id}")
                self.logger.error(stack_trace)
                continue
        self.logger.info('--------------------------------')
        return pd.DataFrame(results)

    def list_contractor_employees(
        self,
        contractor_ids: List[str],
        **kwargs
    ) -> pd.DataFrame:
        """List employees for specific contractors by their IDs.

        Refer to the official Shovels API documentation for detailed
        parameter options:
        https://docs.shovels.ai/api-reference/contractors/list-contractor-employees

        Parameters
        ----------
        contractor_ids : List[str]
            A list of contractor IDs for which to list employees.
        **kwargs : dict, optional
            Keyword arguments passed to the `_make_paginated_request` method.

        Returns
        -------
        pd.DataFrame
            A DataFrame containing employee data for the specified
            contractor IDs.
        """
        url = f"{self.base_url}/contractors/employees"
        results: List[dict] = []
        self.logger.info('--------------------------------')
        self.logger.info(f"Fetching employees for {len(contractor_ids)} contractor IDs: {contractor_ids}")
        for i, contractor_id in enumerate(contractor_ids):
            url = f"{self.base_url}/contractors/{contractor_id}/employees"
            self.logger.info(f"Fetching employees for contractor ID: {contractor_id} ({i+1}/{len(contractor_ids)})")
            try:
                results.extend(self._make_paginated_request(url, None, **kwargs))
            except Exception:
                stack_trace = traceback.format_exc()
                self.logger.error(f"Error fetching employees for contractor ID: {contractor_id}")
                self.logger.error(stack_trace)
                continue
        self.logger.info('--------------------------------')
        return pd.DataFrame(results)
    # endregion: contractor

    # region: permit
    def search_permits(
        self,
        params: dict,
        geo_ids: Iterable[str] | str | None = None,
        **kwargs
    ) -> pd.DataFrame:
        """Search for permits based on specified criteria.

        Refer to the official Shovels API documentation for detailed
        parameter options: https://docs.shovels.ai/api-reference/permits/search-permits

        Parameters
        ----------
        params : dict
            A dictionary of parameters for the search. This typically includes
            filters like `permit_from`, `permit_to`, `tag_id`, `permit_type`,
            `valuation_min`, `valuation_max`, etc.
            The `permit_from` and `permit_to` fields will default to the last
            180 days and today respectively if not provided.
        geo_ids : Iterable[str] or str, optional
            A single Geo ID (string) or an iterable of Geo IDs to search within.
            If None, the search will be performed across all US states (defined
            in `US_STATES`). Default is None.
        **kwargs : dict, optional
            Keyword arguments passed to the `_make_paginated_request` method.

        Returns
        -------
        pd.DataFrame
            A DataFrame containing the search results with permit data.
            An empty DataFrame is returned if no permits are found or
            an error occurs during the process for all geo_ids.
        """
        url = f"{self.base_url}/permits/search"
        if geo_ids is None:
            geo_ids = US_STATES
        if isinstance(geo_ids, str):
            geo_ids = [geo_ids]
        _params = {**params} if params else {}
        _params["permit_from"] = _params.get("permit_from") or (datetime.date.today() - datetime.timedelta(days=180)).strftime("%Y-%m-%d")
        _params["permit_to"] = _params.get("permit_to") or datetime.date.today().strftime("%Y-%m-%d")
        self.logger.info('--------------------------------')
        self.logger.info(f"Fetching permits for {len(geo_ids)} geo_ids: {geo_ids}")
        results: List[dict] = []
        for i, geo_id in enumerate(geo_ids):
            self.logger.info(f"Fetching permits for geo_id: {geo_id} ({i+1}/{len(geo_ids)})")
            try:
                _params["geo_id"] = geo_id
                results.extend(self._make_paginated_request(url, _params, **kwargs))
            except Exception:
                stack_trace = traceback.format_exc()
                self.logger.error(f"Error fetching geo_id {geo_id}")
                self.logger.error(stack_trace)
                continue
        self.logger.info('--------------------------------')
        return pd.DataFrame(results)

    def get_permits_by_id(
        self,
        permit_ids: List[str],
        **kwargs
    ) -> pd.DataFrame:
        """Retrieve detailed information for specific permits by their IDs.

        Refer to the official Shovels API documentation for detailed
        parameter options:
        https://docs.shovels.ai/api-reference/permits/get-permits-by-id

        Parameters
        ----------
        permit_ids : List[str]
            A list of permit IDs to fetch.
        **kwargs : dict, optional
            Keyword arguments passed to the `_make_paginated_request` method.

        Returns
        -------
        pd.DataFrame
            A DataFrame containing the data for the specified permit IDs.
        """
        url = f"{self.base_url}/permits"
        params = {"ids": permit_ids}
        content = self._make_paginated_request(url, params, **kwargs)
        return pd.DataFrame(content)
    # endregion: permit

    def get_tags(self) -> List[dict]:
        """Get all available permit tags.

        Returns
        -------
        List[dict]
            A list of tag objects.
        """
        url = f"{self.base_url}/list/tags"
        content = self._make_request(url, params={"size": 100})
        return content["items"]

    def get_data_release_date(self) -> dict | None:
        """Get the data release date information from the Shovels API.

        Returns
        -------
        dict or None
            A dictionary containing data release date information.
            Returns None if an error occurs.
        """
        url = f"{self.base_url}/meta/release"
        response = self._make_request(url)
        return response
