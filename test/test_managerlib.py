#
# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

import datetime
import time
import unittest
import os
from os import linesep as NEW_LINE

from stubs import StubCertificateDirectory, StubProductCertificate, StubProduct, \
    StubEntitlementCertificate
from subscription_manager.facts import Facts
from subscription_manager.managerlib import merge_pools, PoolFilter, getInstalledProductStatus, \
    LocalTz, parseDate, merge_pools, MergedPoolsStackingGroupSorter
from modelhelpers import create_pool, create_attribute_list
from subscription_manager import managerlib
import stubs
import rhsm
from rhsm.certificate import EntitlementCertificate
from mock import Mock
import xml

cfg = rhsm.config.initConfig()
ENT_CONFIG_DIR = cfg.get('rhsm', 'entitlementCertDir')

#[-]*BEGIN [\w\ ]*[-]* - Find all begin lines
#[-]*BEGIN[\w\ ]*[-]*|[-]*END[\w\ ]*[-]* - Find all BEGIN END lines
#(?P<start>[-]*BEGIN[\w\ ]*[-]*)(?P<content>[^-]*)(?P<end>[-]*END[\w\ ]*[-]*)

EXPECTED_CERT_CONTENT = """-----BEGIN CERTIFICATE-----
MIIJwTCCCSqgAwIBAgIIRW4yerC04nIwDQYJKoZIhvcNAQEFBQAwNDETMBEGA1UE
AwwKbXN0ZWFkLmNzYjELMAkGA1UEBhMCVVMxEDAOBgNVBAcMB1JhbGVpZ2gwHhcN
MTEwNzEzMDAwMDAwWhcNMTIwNzEyMDAwMDAwWjArMSkwJwYDVQQDEyA4MDgwODA4
MDMxMjg1NjIwMDEzMTI5NzZiMDIyMDAwNjCCASIwDQYJKoZIhvcNAQEBBQADggEP
ADCCAQoCggEBAMemhvL5+3/EfoK+Elile3JC6y+FolWJXTxuiuJwO4GXiS5AiIx1
x3sYSZjGvMH2aSopoxrVBLYFTvZ6PmxK6wuV8JVO9pfi5BVpCMwaVosssPAZhFpM
EpM6B/DU2AWSmBk2zvI6PbZ83HzMICByDTUsBLed+HtU6az5rhGXLnUYlnGnau9w
5WkbAbS+hTqZHvWPdwpdMJ/bNyV04xg2LcsnHDSodIVmXgBtQiZD32rGOjkB48QX
mMHnuBpjYiRaZhZCGeOSPI6boSK/pGcr5QdHJB4+NRFSW3INwHHSWjKaTJSRi6+q
LOYGijUKBmv0AE+Bd1acbynxwRPLvcTJATUCAwEAAaOCB18wggdbMBEGCWCGSAGG
+EIBAQQEAwIFoDALBgNVHQ8EBAMCBLAwZAYDVR0jBF0wW4AUooCU0h+EAAGYfSf5
ncDamLLCeUOhOKQ2MDQxEzARBgNVBAMMCm1zdGVhZC5jc2IxCzAJBgNVBAYTAlVT
MRAwDgYDVQQHDAdSYWxlaWdoggkAnVMmeWWGXWwwHQYDVR0OBBYEFKuittOhxG6z
ag5P9cr2fvN+6xIrMBMGA1UdJQQMMAoGCCsGAQUFBwMCMCIGDSsGAQQBkggJAYKh
SQEEEQwPQ2x1c3RlcmluZyBCaXRzMBQGCysGAQQBkggJAgABBAUMA3l1bTAnBgwr
BgEEAZIICQIAAQEEFwwVbmV2ZXItZW5hYmxlZC1jb250ZW50MCcGDCsGAQQBkggJ
AgABAgQXDBVuZXZlci1lbmFibGVkLWNvbnRlbnQwHQYMKwYBBAGSCAkCAAEFBA0M
C3Rlc3QtdmVuZG9yMCEGDCsGAQQBkggJAgABBgQRDA8vZm9vL3BhdGgvbmV2ZXIw
JQYMKwYBBAGSCAkCAAEHBBUMEy9mb28vcGF0aC9uZXZlci9ncGcwEwYMKwYBBAGS
CAkCAAEIBAMMATAwFQYMKwYBBAGSCAkCAAEJBAUMAzYwMDAUBgsrBgEEAZIICQIB
AQQFDAN5dW0wKAYMKwYBBAGSCAkCAQEBBBgMFmFsd2F5cy1lbmFibGVkLWNvbnRl
bnQwKAYMKwYBBAGSCAkCAQECBBgMFmFsd2F5cy1lbmFibGVkLWNvbnRlbnQwHQYM
KwYBBAGSCAkCAQEFBA0MC3Rlc3QtdmVuZG9yMCIGDCsGAQQBkggJAgEBBgQSDBAv
Zm9vL3BhdGgvYWx3YXlzMCYGDCsGAQQBkggJAgEBBwQWDBQvZm9vL3BhdGgvYWx3
YXlzL2dwZzATBgwrBgEEAZIICQIBAQgEAwwBMTAVBgwrBgEEAZIICQIBAQkEBQwD
MjAwMCkGDSsGAQQBkggJAYKhRAEEGAwWQXdlc29tZSBPUyBTZXJ2ZXIgQml0czAU
BgsrBgEEAZIICQICAQQFDAN5dW0wIAYMKwYBBAGSCAkCAgEBBBAMDnRhZ2dlZC1j
b250ZW50MCAGDCsGAQQBkggJAgIBAgQQDA50YWdnZWQtY29udGVudDAdBgwrBgEE
AZIICQICAQUEDQwLdGVzdC12ZW5kb3IwIgYMKwYBBAGSCAkCAgEGBBIMEC9mb28v
cGF0aC9hbHdheXMwJgYMKwYBBAGSCAkCAgEHBBYMFC9mb28vcGF0aC9hbHdheXMv
Z3BnMBMGDCsGAQQBkggJAgIBCAQDDAExMBsGDCsGAQQBkggJAgIBCgQLDAlUQUcx
LFRBRzIwFQYMKwYBBAGSCAkCiFcBBAUMA3l1bTAaBg0rBgEEAZIICQKIVwEBBAkM
B2NvbnRlbnQwIAYNKwYBBAGSCAkCiFcBAgQPDA1jb250ZW50LWxhYmVsMB4GDSsG
AQQBkggJAohXAQUEDQwLdGVzdC12ZW5kb3IwHAYNKwYBBAGSCAkCiFcBBgQLDAkv
Zm9vL3BhdGgwIQYNKwYBBAGSCAkCiFcBBwQQDA4vZm9vL3BhdGgvZ3BnLzAUBg0r
BgEEAZIICQKIVwEIBAMMATEwFAYNKwYBBAGSCAkCiFcBCQQDDAEwMCYGDSsGAQQB
kggJAYKhTgEEFQwTTG9hZCBCYWxhbmNpbmcgQml0czAqBg0rBgEEAZIICQGCoUwB
BBkMF0xhcmdlIEZpbGUgU3VwcG9ydCBCaXRzMCYGDSsGAQQBkggJAYKhSwEEFQwT
U2hhcmVkIFN0b3JhZ2UgQml0czAiBg0rBgEEAZIICQGCoU0BBBEMD01hbmFnZW1l
bnQgQml0czBHBgorBgEEAZIICQQBBDkMN0F3ZXNvbWUgT1MgU2VydmVyIEJ1bmRs
ZWQgKDIgU29ja2V0cywgU3RhbmRhcmQgU3VwcG9ydCkwMAYKKwYBBAGSCAkEAgQi
DCA4MDgwODA4MDMxMjRjMjRlMDEzMTI0YzMxZTdkMDBjMzAtBgorBgEEAZIICQQD
BB8MHWF3ZXNvbWVvcy1zZXJ2ZXItMi1zb2NrZXQtc3RkMBEGCisGAQQBkggJBAUE
AwwBNTAkBgorBgEEAZIICQQGBBYMFDIwMTEtMDctMTNUMDA6MDA6MDBaMCQGCisG
AQQBkggJBAcEFgwUMjAxMi0wNy0xMlQwMDowMDowMFowEgYKKwYBBAGSCAkEDAQE
DAIzMDASBgorBgEEAZIICQQKBAQMAjEyMBsGCisGAQQBkggJBA0EDQwLMTIzMzEx
MzEyMzEwEQYKKwYBBAGSCAkEDgQDDAExMBgGCisGAQQBkggJBA8ECgwIU3RhbmRh
cmQwFQYKKwYBBAGSCAkEEAQHDAVMMS1MMzARBgorBgEEAZIICQQLBAMMATEwNAYK
KwYBBAGSCAkFAQQmDCQ5NGJkZDg2MS0wMzc1LTRhOWEtYTZhMS05M2Y4NGM0ZGZi
NDYwDQYJKoZIhvcNAQEFBQADgYEAiCKjWQKGX9uoMOiG9kn5aPOdhwy2McrefHnS
3qVkcqSxp/LQPTjej+MY7E/XECQInuO14h/RTTWrKReO2nRy9zFFm57fVPt2CjRz
ts/UsltTKEkTD4KBKxFVFELt1KWWT0AE5ire9mWcIdZRlPqvY0EpdmWDsUmX3E5d
oS/s7EY=
-----END CERTIFICATE-----"""

EXPECTED_KEY_CONTENT = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAx6aG8vn7f8R+gr4SWKV7ckLrL4WiVYldPG6K4nA7gZeJLkCI
jHXHexhJmMa8wfZpKimjGtUEtgVO9no+bErrC5XwlU72l+LkFWkIzBpWiyyw8BmE
WkwSkzoH8NTYBZKYGTbO8jo9tnzcfMwgIHINNSwEt534e1TprPmuEZcudRiWcadq
73DlaRsBtL6FOpke9Y93Cl0wn9s3JXTjGDYtyyccNKh0hWZeAG1CJkPfasY6OQHj
xBeYwee4GmNiJFpmFkIZ45I8jpuhIr+kZyvlB0ckHj41EVJbcg3AcdJaMppMlJGL
r6os5gaKNQoGa/QAT4F3VpxvKfHBE8u9xMkBNQIDAQABAoIBABcc5TSN0hrJgafb
Hz6Z8b+ZlaaLvu5OF7geR//M5GatR1lOaUBxhiVu+14va7y8rRIPfe1mScRUuv53
ynA5ABr4QcDXQl71ClicL0OJrQkxpE43dgYKFoBq0G6GBXgnr2oD2VNbgLd2nwPn
kbSP342PSgCDzjdg7ihzQz6QFPXDLVn5wTuJWiUCCg+WqkEUM6DaHirHLLy47vpB
HsA31sE24EiIG8lNNDln4KIp7bZ/A9Lzc9mF/Nwi/EEQq/EAD0rwvTVDkImyYyat
VjVbnANEWYlm/D8ZXmzcwct6Um1jbbJo+8V9eUs97/T2IiKXoYGzgKqwzkSNEnuH
G/3N6OUCgYEA+LzwEVwwV/PoMxe75whbAcRa2xr8qJJT5cqpngV4INUFFqWzyjOO
3rAZrmyq2oN7JqA82PplY3XHoXVojt067Kq2Vqgj+oJtx9WZoACKX5mmU1Zsvxwy
kuPTfQDQ5JkjtS/N/Snls7A7TgOAy97v0Cp4H3UJpXwKKCV7ifd/eqcCgYEAzXq1
0xHu8Q1EYmG8IulyJ2oJFNX92kkPegHheMnFvqUHnmVFbsj8H5E+FQXNQX1aUS1K
1epDN9LlVKBtWF33WGMCFy6VK0v0MGMZGQ+vI/O01MU8d+DBy2HRKz2UPW3OWevX
9udxLASoaCD/3LCn3eeGT5ucRUw12AIQ6zEzTMMCgYEArL1BlzzHkf0gD4N3Cc4i
rYp4cls+ha8BNr9Upho0P9DP9NdkkZLWsE3pt9ldmdzfhIaZWzIhgT4FQlqwHy8C
QeOYN3wTaGB17uanBpf5gMTK3mtRoDLr6FjxwYj0iRzU0Hp/ekZDcFN+DAKgynRr
ZMxpmacE6PjIcPL+5WSNElcCgYBjjKrgipSvtlTGMUGbzGvgyo+Bx7cH9VOJMbYR
9fdWyM9rHvdHmBoGFTD1sGzj6J5EK+RQxQEx33v5xwuSv1uhN76AirH8Wv0AIFK9
gIrCqUSXvMLx9TMOnOJgx6G1LSjHCesElNaQk+UfJbWwLun1KUE5+lL4g9amQ0H9
IEYRTwKBgQCXpMJ2P0bomDQMeIou2CSGCuEMcx8NuTA9x4t6xrf6Hyv7O9K7+fr1
5aNLpomnn09oQvg9Siz+AMzVEUkkbYmiHf3lDng/RE00hW32SDLJMloJEFmQLCrV
ufxBTlg4v0B3xS1GgvATMY4hyk53o5PffmlRO03dbfpGK/rkTIPwFg==
-----END RSA PRIVATE KEY-----"""

EXPECTED_CERT = EntitlementCertificate(EXPECTED_CERT_CONTENT)


class MergePoolsTests(unittest.TestCase):

    def test_single_pool(self):
        product = 'product1'
        pools = [
                create_pool(product, product, quantity=10, consumed=5)
        ]
        results = merge_pools(pools)
        self.assertEquals(1, len(results.values()))
        result = results.values()[0]
        self.assertEquals(product, result.product_id)

    def test_multiple_pools(self):
        product1 = 'product1'
        product2 = 'product2'
        pools = [
                create_pool(product1, product1, quantity=10, consumed=5),
                create_pool(product1, product1, quantity=55, consumed=20),
                create_pool(product2, product2, quantity=10, consumed=5),
        ]
        results = merge_pools(pools)
        self.assertEquals(2, len(results.values()))
        self.assertTrue(product1 in results)
        self.assertTrue(product2 in results)

        # Check product1:
        merged_pools = results[product1]
        self.assertEquals(product1, merged_pools.product_id)
        self.assertEquals(65, merged_pools.quantity)
        self.assertEquals(25, merged_pools.consumed)

        # Check product2:
        merged_pools = results[product2]
        self.assertEquals(product2, merged_pools.product_id)
        self.assertEquals(10, merged_pools.quantity)
        self.assertEquals(5, merged_pools.consumed)


class PoolFilterTests(unittest.TestCase):

    def test_uninstalled_filter_direct_match(self):
        product1 = 'product1'
        product2 = 'product2'

        pd = StubCertificateDirectory([
            StubProductCertificate(StubProduct(product2))])
        pool_filter = PoolFilter(product_dir=pd,
                entitlement_dir=StubCertificateDirectory([]))

        pools = [
                create_pool(product1, product1),
                create_pool(product1, product1),
                create_pool(product2, product2),
        ]
        result = pool_filter.filter_out_uninstalled(pools)
        self.assertEquals(1, len(result))
        self.assertEquals(product2, result[0]['productId'])

    def test_uninstalled_filter_provided_match(self):
        product1 = 'product1'
        product2 = 'product2'
        provided = 'providedProduct'
        pd = StubCertificateDirectory([
            StubProductCertificate(StubProduct(provided))])
        pool_filter = PoolFilter(product_dir=pd,
                entitlement_dir=StubCertificateDirectory([]))

        pools = [
                create_pool(product1, product1),
                create_pool(product2, product2, provided_products=[provided]),
        ]
        result = pool_filter.filter_out_uninstalled(pools)
        self.assertEquals(1, len(result))
        self.assertEquals(product2, result[0]['productId'])

    def test_installed_filter_direct_match(self):
        product1 = 'product1'
        product2 = 'product2'
        pd = StubCertificateDirectory([
            StubProductCertificate(StubProduct(product2))])
        pool_filter = PoolFilter(product_dir=pd,
                entitlement_dir=StubCertificateDirectory([]))

        pools = [
                create_pool(product1, product1),
                create_pool(product1, product1),
                create_pool(product2, product2),
        ]
        result = pool_filter.filter_out_installed(pools)
        self.assertEquals(1, len(result))
        self.assertEquals(product1, result[0]['productId'])

    def test_installed_filter_provided_match(self):
        product1 = 'product1'
        product2 = 'product2'
        provided = 'providedProduct'
        pd = StubCertificateDirectory([
            StubProductCertificate(StubProduct(provided))])
        pool_filter = PoolFilter(product_dir=pd,
                entitlement_dir=StubCertificateDirectory([]))

        pools = [
                create_pool(product1, product1),
                create_pool(product2, product2, provided_products=[provided]),
        ]
        result = pool_filter.filter_out_installed(pools)
        self.assertEquals(1, len(result))
        self.assertEquals(product1, result[0]['productId'])

    def test_installed_filter_multi_match(self):
        product1 = 'product1'
        product2 = 'product2'
        provided = 'providedProduct'
        pd = StubCertificateDirectory([
            StubProductCertificate(StubProduct(provided)),
            StubProductCertificate(StubProduct(product2))])
        pool_filter = PoolFilter(product_dir=pd,
                entitlement_dir=StubCertificateDirectory([]))

        pools = [
                create_pool(product1, product1),
                create_pool(product2, product2, provided_products=[provided]),
        ]
        result = pool_filter.filter_out_installed(pools)
        self.assertEquals(1, len(result))
        self.assertEquals(product1, result[0]['productId'])

    def test_filter_product_name(self):
        product1 = 'Foo Product'
        product2 = 'Bar Product'
        pd = StubCertificateDirectory([])
        pool_filter = PoolFilter(product_dir=pd,
                entitlement_dir=StubCertificateDirectory([]))

        pools = [
                create_pool(product1, product1),
                create_pool(product2, product2),
        ]
        result = pool_filter.filter_product_name(pools, "Foo")
        self.assertEquals(1, len(result))
        self.assertEquals(product1, result[0]['productId'])

    def test_filter_product_name_matches_provided(self):
        product1 = 'Foo Product'
        product2 = 'Bar Product'
        pd = StubCertificateDirectory([])
        pool_filter = PoolFilter(product_dir=pd,
                entitlement_dir=StubCertificateDirectory([]))

        pools = [
                create_pool(product1, product1, provided_products=[product2]),
        ]
        result = pool_filter.filter_product_name(pools, "Bar")
        self.assertEquals(1, len(result))
        self.assertEquals(product1, result[0]['productId'])


class InstalledProductStatusTests(unittest.TestCase):

    def test_entitlement_for_not_installed_product_shows_not_installed(self):
        product_directory = StubCertificateDirectory([])
        entitlement_directory = StubCertificateDirectory([
            StubEntitlementCertificate(StubProduct("product1"))])

        product_status = getInstalledProductStatus(product_directory,
                entitlement_directory)

        # no product certs installed...
        self.assertEquals(0, len(product_status))

    def test_entitlement_for_installed_product_shows_subscribed(self):
        product = StubProduct("product1")
        product_directory = StubCertificateDirectory([
            StubProductCertificate(product)])
        entitlement_directory = StubCertificateDirectory([
            StubEntitlementCertificate(product, sockets=10)])

        product_status = getInstalledProductStatus(product_directory,
                entitlement_directory)

        self.assertEquals(1, len(product_status))
        self.assertEquals("subscribed", product_status[0][4])

    def test_expired_entitlement_for_installed_product_shows_expired(self):
        product = StubProduct("product1")
        product_directory = StubCertificateDirectory([
            StubProductCertificate(product)])
        entitlement_directory = StubCertificateDirectory([
            StubEntitlementCertificate(product,
                end_date=(datetime.datetime.now() - datetime.timedelta(days=2)))])

        product_status = getInstalledProductStatus(product_directory,
                entitlement_directory)

        self.assertEquals(1, len(product_status))
        self.assertEquals("expired", product_status[0][4])

    def test_no_entitlement_for_installed_product_shows_no_subscribed(self):
        product = StubProduct("product1")
        product_directory = StubCertificateDirectory([
            StubProductCertificate(product)])
        entitlement_directory = StubCertificateDirectory([])

        product_status = getInstalledProductStatus(product_directory,
                entitlement_directory)

        self.assertEquals(1, len(product_status))
        self.assertEquals("not_subscribed", product_status[0][4])

    def test_future_dated_entitlement_shows_future_subscribed(self):
        product = StubProduct("product1")
        product_directory = StubCertificateDirectory([
                StubProductCertificate(product)])
        entitlement_directory = StubCertificateDirectory([
                StubEntitlementCertificate(product,
                    start_date=(datetime.datetime.now() + datetime.timedelta(days=1365)))])

        product_status = getInstalledProductStatus(product_directory,
                                                   entitlement_directory)
        self.assertEquals(1, len(product_status))
        self.assertEquals("future_subscribed", product_status[0][4])

    def test_one_product_with_two_entitlements_lists_product_twice(self):
        product = StubProduct("product1")
        product_directory = StubCertificateDirectory([
            StubProductCertificate(product)])
        entitlement_directory = StubCertificateDirectory([
            StubEntitlementCertificate(product),
            StubEntitlementCertificate(product)
        ])

        product_status = getInstalledProductStatus(product_directory,
                entitlement_directory)

        # only "product" is installed
        self.assertEquals(1, len(product_status))

    def test_one_subscription_with_bundled_products_lists_once(self):
        product1 = StubProduct("product1")
        product2 = StubProduct("product2")
        product3 = StubProduct("product3")
        product_directory = StubCertificateDirectory([
            StubProductCertificate(product1)])
        entitlement_directory = StubCertificateDirectory([
            StubEntitlementCertificate(product1, [product2, product3],
            sockets=10)
        ])

        product_status = getInstalledProductStatus(product_directory,
                entitlement_directory)

        # neither product3 or product 2 are installed
        self.assertEquals(1, len(product_status))
#        self.assertEquals("product3", product_status[0][0])
#        self.assertEquals("Not Installed", product_status[0][3])
 #       self.assertEquals("product2", product_status[1][0])
 #       self.assertEquals("Not Installed", product_status[1][3])
        self.assertEquals("product1", product_status[0][0])
        self.assertEquals("subscribed", product_status[0][4])

    def test_one_subscription_with_bundled_products_lists_once_part_two(self):
        product1 = StubProduct("product1")
        product2 = StubProduct("product2")
        product3 = StubProduct("product3")
        product_directory = StubCertificateDirectory([
            StubProductCertificate(product1), StubProductCertificate(product2)])
        entitlement_directory = StubCertificateDirectory([
            StubEntitlementCertificate(product1, [product2, product3],
            sockets=10)
        ])

        product_status = getInstalledProductStatus(product_directory,
                entitlement_directory)

        # product3 isn't installed
        self.assertEquals(2, len(product_status))
        #self.assertEquals("product3", product_status[0][0])
        #self.assertEquals("Not Installed", product_status[0][3])
        self.assertEquals("product2", product_status[0][0])
        self.assertEquals("subscribed", product_status[0][4])
        self.assertEquals("product1", product_status[1][0])
        self.assertEquals("subscribed", product_status[1][4])


class TestParseDate(unittest.TestCase):
    def _test_local_tz(self):
        tz = LocalTz()
        dt_no_tz = datetime.datetime(year=2000, month=1, day=1, hour=12, minute=34)
        now_dt = datetime.datetime(year=2000, month=1, day=1, hour=12, minute=34, tzinfo=tz)
        parseDate(now_dt.isoformat())
        # last member is is_dst, which is -1, if there is no tzinfo, which
        # we expect for dt_no_tz
        #
        # see if we get the same times
        now_dt_tt = now_dt.timetuple()
        dt_no_tz_tt = dt_no_tz.timetuple()

        # tm_isdst (timpletuple()[8]) is 0 if a tz is set,
        # but the dst offset is 0
        # if it is -1, no timezone is set
        if now_dt_tt[8] == 1 and dt_no_tz_tt == -1:
            # we are applying DST to now time, but not no_tz time, so
            # they will be off by an hour. This is kind of weird
            self.assertEquals(now_dt_tt[:2], dt_no_tz_tt[:2])
            self.assertEquals(now_dt_tt[4:7], dt_no_tz_tt[4:7])

            # add an hour for comparisons
            dt_no_tz_dst = dt_no_tz
            dt_no_tz_dst = dt_no_tz + datetime.timedelta(hours=1)
            self.assertEquals(now_dt_tt[3], dt_no_tz_dst.timetuple()[3])
        else:
            self.assertEquals(now_dt_tt[:7], dt_no_tz_tt[:7])

    def test_local_tz_now(self):
        self._test_local_tz()

    def test_local_tz_not_dst(self):
        time.daylight = 0
        self._test_local_tz()

    def test_local_tz_dst(self):
        time.daylight = 1
        self._test_local_tz()

    def test_server_date_utc_timezone(self):
        # sample date from json response from server
        server_date = "2012-04-10T00:00:00.000+0000"
        dt = parseDate(server_date)
        # no dst
        self.assertEquals(datetime.timedelta(seconds=0), dt.tzinfo.dst(dt))
        # it's a utc date, no offset
        self.assertEquals(datetime.timedelta(seconds=0), dt.tzinfo.utcoffset(dt))

    def test_server_date_est_timezone(self):
        est_date = "2012-04-10T00:00:00.000-04:00"
        dt = parseDate(est_date)
        self.assertEquals(datetime.timedelta(hours=4), dt.tzinfo.utcoffset(dt))


# http://docs.python.org/library/datetime.html
# trying to verify the behaviour for dst() there
class TestLocalTz(unittest.TestCase):
    def _testDst(self):
        tz = LocalTz()
        epoch = time.time()
        now_dt = datetime.datetime.fromtimestamp(epoch, tz=tz)
        diff_now = tz.utcoffset(now_dt) - tz.dst(now_dt)
        td = datetime.timedelta(weeks=26)
        dt = now_dt + td

        diff_six_months = tz.utcoffset(dt) - tz.dst(dt)

        week_ago_dt = dt - datetime.timedelta(weeks=4)
        diff_week_ago = tz.utcoffset(week_ago_dt) - tz.dst(week_ago_dt)

        print diff_now, diff_six_months, diff_week_ago
        self.assertEquals(diff_now, diff_six_months)
        self.assertEquals(diff_six_months, diff_week_ago)

    def testDst(self):
        time.daylight = 1
        self._testDst()

    def testNoDst(self):
        time.daylight = 0
        self._testDst()


class MockLog:
    def info(self):
        pass


def MockSystemLog(self, message, priority):
    pass

EXPECTED_CONTENT = EXPECTED_CERT_CONTENT + NEW_LINE + EXPECTED_KEY_CONTENT


class ExtractorStub(managerlib.ImportFileExtractor):

    def __init__(self, content, file_path="test/file/path"):
        self.content = content
        self.writes = []
        managerlib.ImportFileExtractor.__init__(self, file_path)

    # Stub out any file system access
    def _read(self, file_path):
        return self.content

    def _write_file(self, target, content):
        self.writes.append((target, content))

    def _ensure_entitlement_dir_exists(self):
        # Do nothing but stub out the dir check to avoid file system access.
        pass


class TestImportFileExtractor(unittest.TestCase):

    def test_contains_key_content_when_key_and_cert_exists_in_import_file(self):
        extractor = ExtractorStub(EXPECTED_CONTENT)
        self.assertTrue(extractor.contains_key_content());

    def test_does_not_contain_key_when_key_does_not_exist_in_import_file(self):
        extractor = ExtractorStub(EXPECTED_CERT_CONTENT)
        self.assertFalse(extractor.contains_key_content());

    def test_get_key_content_when_key_exists(self):
        extractor = ExtractorStub(EXPECTED_CONTENT, file_path="12345.pem")
        self.assertTrue(extractor.contains_key_content())
        self.assertEquals(EXPECTED_KEY_CONTENT, extractor.get_key_content())

    def test_get_key_content_returns_None_when_key_does_not_exist(self):
        extractor = ExtractorStub(EXPECTED_CERT_CONTENT, file_path="12345.pem")
        self.assertFalse(extractor.get_key_content())

    def test_get_cert_content(self):
        extractor = ExtractorStub(EXPECTED_CONTENT, file_path="12345.pem")
        self.assertTrue(extractor.contains_key_content())
        self.assertEquals(EXPECTED_CERT_CONTENT, extractor.get_cert_content())

    def test_get_cert_content_returns_None_when_cert_does_not_exist(self):
        extractor = ExtractorStub(EXPECTED_KEY_CONTENT, file_path="12345.pem")
        self.assertFalse(extractor.get_cert_content())

    def test_verify_valid_entitlement_for_valid_cert(self):
        extractor = ExtractorStub(EXPECTED_CONTENT, file_path="12345.pem")
        self.assertTrue(extractor.verify_valid_entitlement())

    def test_verify_valid_entitlement_for_invalid_cert(self):
        extractor = ExtractorStub(EXPECTED_KEY_CONTENT, file_path="12345.pem")
        self.assertFalse(extractor.verify_valid_entitlement())

    def test_verify_valid_entitlement_for_no_key(self):
        extractor = ExtractorStub(EXPECTED_CERT_CONTENT, file_path="12345.pem")
        self.assertFalse(extractor.verify_valid_entitlement())

    def test_verify_valid_entitlement_for_no_cert_content(self):
        extractor = ExtractorStub("", file_path="12345.pem")
        self.assertFalse(extractor.verify_valid_entitlement())

    def test_write_cert_only(self):
        expected_cert_file = "%d.pem" % (EXPECTED_CERT.serialNumber())
        extractor = ExtractorStub(EXPECTED_CERT_CONTENT, file_path=expected_cert_file)
        extractor.write_to_disk()

        self.assertEquals(1, len(extractor.writes))

        write_one = extractor.writes[0]
        self.assertEquals(os.path.join(ENT_CONFIG_DIR, expected_cert_file), write_one[0])
        self.assertEquals(EXPECTED_CERT_CONTENT, write_one[1])

    def test_write_key_and_cert(self):
        filename = "%d.pem" % (EXPECTED_CERT.serialNumber())
        self._assert_correct_cert_and_key_files_generated_with_filename(filename)

    def test_file_renamed_when_imported_with_serial_no_and_custom_extension(self):
        filename = "%d.cert" % (EXPECTED_CERT.serialNumber())
        self._assert_correct_cert_and_key_files_generated_with_filename(filename)

    def test_file_renamed_when_imported_with_serial_no_and_no_extension(self):
        filename = str(EXPECTED_CERT.serialNumber())
        self._assert_correct_cert_and_key_files_generated_with_filename(filename)

    def test_file_renamed_when_imported_with_custom_name_and_pem_extension(self):
        filename = "entitlement.pem"
        self._assert_correct_cert_and_key_files_generated_with_filename(filename)

    def test_file_renamed_when_imported_with_custom_name_no_extension(self):
        filename = "entitlement"
        self._assert_correct_cert_and_key_files_generated_with_filename(filename)

    def _assert_correct_cert_and_key_files_generated_with_filename(self, filename):
        expected_file_prefix = "%d" % (EXPECTED_CERT.serialNumber())
        expected_cert_file = expected_file_prefix + ".pem"
        expected_key_file = expected_file_prefix + "-key.pem"

        extractor = ExtractorStub(EXPECTED_CONTENT, file_path=filename)
        extractor.write_to_disk()

        self.assertEquals(2, len(extractor.writes))

        write_one = extractor.writes[0]
        self.assertEquals(os.path.join(ENT_CONFIG_DIR, expected_cert_file), write_one[0])
        self.assertEquals(EXPECTED_CERT_CONTENT, write_one[1])

        write_two = extractor.writes[1]
        self.assertEquals(os.path.join(ENT_CONFIG_DIR, expected_key_file), write_two[0])
        self.assertEquals(EXPECTED_KEY_CONTENT, write_two[1])


class TestMergedPoolsStackingGroupSorter(unittest.TestCase):

    def test_sorter_adds_group_for_non_stackable_entitlement(self):
        pool = self._create_pool("test-prod-1", "Test Prod 1")
        merged = merge_pools([pool])
        pools = merged.values()
        sorter = MergedPoolsStackingGroupSorter(pools)

        self.assertEquals(1, len(sorter.groups))
        group = sorter.groups[0]
        self.assertEquals("", group.name)
        self.assertEquals(1, len(group.entitlements))
        self.assertEquals(pools[0], group.entitlements[0])

    def test_sorter_adds_group_for_stackable_entitlement(self):
        expected_stacking_id = 1234
        pool = self._create_pool("test-prod-1", "Test Prod 1", expected_stacking_id)
        merged = merge_pools([pool])
        pools = merged.values()
        sorter = MergedPoolsStackingGroupSorter(pools)

        self.assertEquals(1, len(sorter.groups))
        group = sorter.groups[0]
        self.assertEquals("Test Prod 1", group.name)
        self.assertEquals(1, len(group.entitlements))
        self.assertEquals(pools[0], group.entitlements[0])

    def test_sorter_adds_multiple_entitlements_to_group_when_same_stacking_id(self):
        expected_stacking_id = 1234
        pool1 = self._create_pool("test-prod-1", "Test Prod 1", expected_stacking_id)
        pool2 = self._create_pool("test-prod-2", "Test Prod 2", expected_stacking_id)

        merged = merge_pools([pool1, pool2])

        pools = merged.values()
        sorter = MergedPoolsStackingGroupSorter(pools)

        self.assertEquals(1, len(sorter.groups))
        group = sorter.groups[0]

        self.assertEquals("Test Prod 2", group.name)
        self.assertEquals(2, len(group.entitlements))

        self.assertEquals(pools[0], group.entitlements[0])
        self.assertEquals(pools[1], group.entitlements[1])

    def test_sorter_adds_multiple_groups_for_non_stacking_entitlements(self):
        pool1 = self._create_pool("test-prod-1", "Test Prod 1")
        pool2 = self._create_pool("test-prod-2", "Test Prod 2")

        merged = merge_pools([pool1, pool2])
        pools = merged.values()
        sorter = MergedPoolsStackingGroupSorter(pools)

        self.assertEquals(2, len(sorter.groups))
        group1 = sorter.groups[0]
        group2 = sorter.groups[1]

        self.assertEquals("", group1.name)
        self.assertEquals(1, len(group1.entitlements))
        self.assertEquals(pools[0], group1.entitlements[0])

        self.assertEquals("", group2.name)
        self.assertEquals(1, len(group2.entitlements))
        self.assertEquals(pools[1], group2.entitlements[0])

    def test_stacking_and_non_stacking_groups_created(self):
        pool1 = self._create_pool("test-prod-1", "Test Prod 1")

        expected_stacking_id = 1234
        pool2 = self._create_pool("test-prod-2", "Test Prod 2", expected_stacking_id)

        merged = merge_pools([pool1, pool2])
        pools = merged.values()
        sorter = MergedPoolsStackingGroupSorter(pools)

        self.assertEquals(2, len(sorter.groups))
        group1 = sorter.groups[0]
        group2 = sorter.groups[1]

        self.assertEquals("Test Prod 2", group1.name)
        self.assertEquals(1, len(group1.entitlements))
        self.assertEquals(pools[0], group1.entitlements[0])

        self.assertEquals("", group2.name)
        self.assertEquals(1, len(group2.entitlements))
        self.assertEquals(pools[1], group2.entitlements[0])

    def _create_pool(self, product_id, product_name, stacking_id=None):
        prod_attrs = []
        if stacking_id:
            stacking_id_attribute = {
                "name": "stacking_id",
                "value": stacking_id
            }
            prod_attrs.append(stacking_id_attribute)
        return create_pool(product_id, product_name, productAttributes=prod_attrs)


class ParseDateTests(unittest.TestCase):

    def test_2038_bug(self):
        # About to monkey patch, store a reference to function so we can
        # restore it.
        function = xml.utils.iso8601.parse
        xml.utils.iso8601.parse = Mock(side_effect=OverflowError())
        parsed = parseDate("9999-09-06T00:00:00.000+0000")
        xml.utils.iso8601.parse = function

        # Simulated a 32-bit date overflow, date should have been
        # replaced by one that does not overflow:
        self.assertEquals(2038, parsed.year)
        self.assertEquals(1, parsed.month)
        self.assertEquals(1, parsed.day)
