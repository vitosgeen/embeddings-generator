========================================================================================================================================================= FAILURES ==========================================================================================================================================================
___________________________________________________________________________________________________________________________________ TestEmbedEndpointChunking.test_short_text_no_chunking ___________________________________________________________________________________________________________________________________
tests/integration/test_chunking_api.py:43: in test_short_text_no_chunking
    assert response.status_code == 200
E   assert 401 == 200
E    +  where 401 = <Response [401]>.status_code
__________________________________________________________________________________________________________________________ TestEmbedEndpointChunking.test_long_text_without_chunking_shows_warning __________________________________________________________________________________________________________________________
tests/integration/test_chunking_api.py:65: in test_long_text_without_chunking_shows_warning
    assert response.status_code == 200
E   assert 401 == 200
E    +  where 401 = <Response [401]>.status_code
________________________________________________________________________________________________________________________________ TestEmbedEndpointChunking.test_long_text_with_auto_chunking ________________________________________________________________________________________________________________________________
tests/integration/test_chunking_api.py:90: in test_long_text_with_auto_chunking
    assert response.status_code == 200
E   assert 401 == 200
E    +  where 401 = <Response [401]>.status_code
_______________________________________________________________________________________________________________________________ TestEmbedEndpointChunking.test_very_long_text_multiple_chunks _______________________________________________________________________________________________________________________________
tests/integration/test_chunking_api.py:119: in test_very_long_text_multiple_chunks
    assert response.status_code == 200
E   assert 401 == 200
E    +  where 401 = <Response [401]>.status_code
___________________________________________________________________________________________________________________________________ TestEmbedEndpointChunking.test_combine_method_average ___________________________________________________________________________________________________________________________________
tests/integration/test_chunking_api.py:140: in test_combine_method_average
    assert response.status_code == 200
E   assert 401 == 200
E    +  where 401 = <Response [401]>.status_code
__________________________________________________________________________________________________________________________________ TestEmbedEndpointChunking.test_combine_method_weighted ___________________________________________________________________________________________________________________________________
tests/integration/test_chunking_api.py:158: in test_combine_method_weighted
    assert response.status_code == 200
E   assert 401 == 200
E    +  where 401 = <Response [401]>.status_code
_____________________________________________________________________________________________________________________________________ TestEmbedEndpointChunking.test_combine_method_max _____________________________________________________________________________________________________________________________________
tests/integration/test_chunking_api.py:176: in test_combine_method_max
    assert response.status_code == 200
E   assert 401 == 200
E    +  where 401 = <Response [401]>.status_code
____________________________________________________________________________________________________________________________________ TestEmbedEndpointChunking.test_combine_method_first ____________________________________________________________________________________________________________________________________
tests/integration/test_chunking_api.py:194: in test_combine_method_first
    assert response.status_code == 200
E   assert 401 == 200
E    +  where 401 = <Response [401]>.status_code
__________________________________________________________________________________________________________________________________ TestEmbedEndpointChunking.test_return_individual_chunks __________________________________________________________________________________________________________________________________
tests/integration/test_chunking_api.py:212: in test_return_individual_chunks
    assert response.status_code == 200
E   assert 401 == 200
E    +  where 401 = <Response [401]>.status_code
_____________________________________________________________________________________________________________________________________ TestEmbedEndpointChunking.test_custom_chunk_size ______________________________________________________________________________________________________________________________________
tests/integration/test_chunking_api.py:243: in test_custom_chunk_size
    assert response.status_code == 200
E   assert 401 == 200
E    +  where 401 = <Response [401]>.status_code
________________________________________________________________________________________________________________________________________ TestEmbedEndpointChunking.test_zero_overlap ________________________________________________________________________________________________________________________________________
tests/integration/test_chunking_api.py:265: in test_zero_overlap
    assert response.status_code == 200
E   assert 401 == 200
E    +  where 401 = <Response [401]>.status_code
_______________________________________________________________________________________________________________________________________ TestEmbedCheckEndpoint.test_check_short_text ________________________________________________________________________________________________________________________________________
tests/integration/test_chunking_api.py:285: in test_check_short_text
    assert response.status_code == 200
E   assert 404 == 200
E    +  where 404 = <Response [404]>.status_code
________________________________________________________________________________________________________________________________________ TestEmbedCheckEndpoint.test_check_long_text ________________________________________________________________________________________________________________________________________
tests/integration/test_chunking_api.py:305: in test_check_long_text
    assert response.status_code == 200
E   assert 404 == 200
E    +  where 404 = <Response [404]>.status_code
_________________________________________________________________________________________________________________________________ TestEmbedCheckEndpoint.test_check_matches_actual_chunking _________________________________________________________________________________________________________________________________
tests/integration/test_chunking_api.py:343: in test_check_matches_actual_chunking
    assert check_data["would_be_chunked"] == embed_data["was_chunked"]
E   KeyError: 'would_be_chunked'
___________________________________________________________________________________________________________________________________________ TestChunkingEdgeCases.test_empty_text ___________________________________________________________________________________________________________________________________________
tests/integration/test_chunking_api.py:363: in test_empty_text
    assert response.status_code in [200, 400, 422]
E   assert 401 in [200, 400, 422]
E    +  where 401 = <Response [401]>.status_code
_____________________________________________________________________________________________________________________________________ TestChunkingEdgeCases.test_unicode_text_chunking ______________________________________________________________________________________________________________________________________
tests/integration/test_chunking_api.py:378: in test_unicode_text_chunking
    assert response.status_code == 200
E   assert 401 == 200
E    +  where 401 = <Response [401]>.status_code
_______________________________________________________________________________________________________________________________________ TestChunkingEdgeCases.test_text_with_newlines _______________________________________________________________________________________________________________________________________
tests/integration/test_chunking_api.py:395: in test_text_with_newlines
    assert response.status_code == 200
E   assert 401 == 200
E    +  where 401 = <Response [401]>.status_code
________________________________________________________________________________________________________________________________________ TestChunkingEdgeCases.test_exactly_at_limit ________________________________________________________________________________________________________________________________________
tests/integration/test_chunking_api.py:413: in test_exactly_at_limit
    assert response.status_code == 200
E   assert 401 == 200
E    +  where 401 = <Response [401]>.status_code
_____________________________________________________________________________________________________________________________________ TestChunkingEdgeCases.test_invalid_combine_method _____________________________________________________________________________________________________________________________________
tests/integration/test_chunking_api.py:432: in test_invalid_combine_method
    assert response.status_code == 500
E   assert 401 == 500
E    +  where 401 = <Response [401]>.status_code
_______________________________________________________________________________________________________________________________________ TestChunkingPerformance.test_very_large_text ________________________________________________________________________________________________________________________________________
tests/integration/test_chunking_api.py:454: in test_very_large_text
    assert response.status_code == 200
E   assert 401 == 200
E    +  where 401 = <Response [401]>.status_code
____________________________________________________________________________________________________________________________________ TestChunkingPerformance.test_chunk_count_reasonable ____________________________________________________________________________________________________________________________________
tests/integration/test_chunking_api.py:475: in test_chunk_count_reasonable
    assert response.status_code == 200
E   assert 401 == 200
E    +  where 401 = <Response [401]>.status_code
================================================================================================================================================== short test summary info ==================================================================================================================================================
FAILED tests/integration/test_chunking_api.py::TestEmbedEndpointChunking::test_short_text_no_chunking - assert 401 == 200
FAILED tests/integration/test_chunking_api.py::TestEmbedEndpointChunking::test_long_text_without_chunking_shows_warning - assert 401 == 200
FAILED tests/integration/test_chunking_api.py::TestEmbedEndpointChunking::test_long_text_with_auto_chunking - assert 401 == 200
FAILED tests/integration/test_chunking_api.py::TestEmbedEndpointChunking::test_very_long_text_multiple_chunks - assert 401 == 200
FAILED tests/integration/test_chunking_api.py::TestEmbedEndpointChunking::test_combine_method_average - assert 401 == 200
FAILED tests/integration/test_chunking_api.py::TestEmbedEndpointChunking::test_combine_method_weighted - assert 401 == 200
FAILED tests/integration/test_chunking_api.py::TestEmbedEndpointChunking::test_combine_method_max - assert 401 == 200
FAILED tests/integration/test_chunking_api.py::TestEmbedEndpointChunking::test_combine_method_first - assert 401 == 200
FAILED tests/integration/test_chunking_api.py::TestEmbedEndpointChunking::test_return_individual_chunks - assert 401 == 200
FAILED tests/integration/test_chunking_api.py::TestEmbedEndpointChunking::test_custom_chunk_size - assert 401 == 200
FAILED tests/integration/test_chunking_api.py::TestEmbedEndpointChunking::test_zero_overlap - assert 401 == 200
FAILED tests/integration/test_chunking_api.py::TestEmbedCheckEndpoint::test_check_short_text - assert 404 == 200
FAILED tests/integration/test_chunking_api.py::TestEmbedCheckEndpoint::test_check_long_text - assert 404 == 200
FAILED tests/integration/test_chunking_api.py::TestEmbedCheckEndpoint::test_check_matches_actual_chunking - KeyError: 'would_be_chunked'
FAILED tests/integration/test_chunking_api.py::TestChunkingEdgeCases::test_empty_text - assert 401 in [200, 400, 422]
FAILED tests/integration/test_chunking_api.py::TestChunkingEdgeCases::test_unicode_text_chunking - assert 401 == 200
FAILED tests/integration/test_chunking_api.py::TestChunkingEdgeCases::test_text_with_newlines - assert 401 == 200
FAILED tests/integration/test_chunking_api.py::TestChunkingEdgeCases::test_exactly_at_limit - assert 401 == 200
FAILED tests/integration/test_chunking_api.py::TestChunkingEdgeCases::test_invalid_combine_method - assert 401 == 500
FAILED tests/integration/test_chunking_api.py::TestChunkingPerformance::test_very_large_text - assert 401 == 200
FAILED tests/integration/test_chunking_api.py::TestChunkingPerformance::test_chunk_count_reasonable - assert 401 == 200
======================================================================================================================================== 21 failed, 189 passed in 131.88s (0:02:11)