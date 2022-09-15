import unittest

from ob.data_colection.base_components.tree_base_broker_default_target import TreeBaseBrokerDefaultTarget
from ob.data_colection.base_components.tree_provider import TreeProvider
from ob.data_colection.value_call import ValueRequest


class TreeBaseBrokerDefaultTargetTest(unittest.TestCase):

    def test_get_provider(self):
        p_name1 = 'p1'
        provider1 = TreeProvider(component_name=p_name1, source_name=p_name1)
        p_name2 = 'p2'
        provider2 = TreeProvider(component_name=p_name2, source_name=p_name2)
        default_p_name = 'default'
        de_provider = TreeProvider(component_name=default_p_name, source_name=default_p_name)
        vb = TreeBaseBrokerDefaultTarget('sample_name',
                                         list_providers=[provider1, provider2],
                                         default_provider=de_provider)
        # get default provider
        request = ValueRequest('.'.join(['non_existing_address', 'some_val']), 1661349399.030824, 20)
        provider = vb._get_provider(request)
        self.assertEqual(provider.get_source_name(), de_provider.get_source_name())
        self.assertIs(provider, de_provider)
        # get normal provider
        request = ValueRequest('.'.join([p_name2, 'some_val']), 1661349399.030824, 20)
        provider = vb._get_provider(request)
        self.assertEqual(provider.get_source_name(), provider2.get_source_name())
        self.assertIs(provider, provider2)


if __name__ == '__main__':
    unittest.main()
