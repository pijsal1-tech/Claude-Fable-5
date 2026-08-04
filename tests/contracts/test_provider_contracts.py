# -*- coding: utf-8 -*-
"""T-010 (R-103): apply ProviderContractMixin to every registered provider.

One test class per provider — the mixin's checks run for each. FakeProvider
(the test double) and MockProvider (in-tree double) are held to the same
contract so tests can't drift from production behavior either.
"""
from providers.base import MockProvider
from providers.genspark import GensparkProvider
from providers.deepseek import DeepSeekProvider
from providers.use_ai import UseAIProvider
from providers.alle_ai import AlleAIProvider
from providers.openai_compat import OpenAICompatProvider
from tests.fakes.fake_provider import FakeProvider

from tests.contracts.provider_contract import ProviderContractMixin


class TestGensparkContract(ProviderContractMixin):
    provider_cls = GensparkProvider


class TestDeepSeekContract(ProviderContractMixin):
    provider_cls = DeepSeekProvider


class TestUseAIContract(ProviderContractMixin):
    provider_cls = UseAIProvider


class TestAlleAIContract(ProviderContractMixin):
    provider_cls = AlleAIProvider


class TestOpenAICompatContract(ProviderContractMixin):
    # TSK-735b (D-19 القرار 7 / D-20): المزود العام بمفتاح API —
    # يخضع لنفس عقد T-010 ككل مزود مسجَّل (توجيه check.sh).
    provider_cls = OpenAICompatProvider


class TestMockProviderContract(ProviderContractMixin):
    provider_cls = MockProvider


class TestFakeProviderContract(ProviderContractMixin):
    provider_cls = FakeProvider
