######################################################################
# Copyright 2016, 2023 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################
"""
Product API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
  codecov --token=$CODECOV_TOKEN

  While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_service.py:TestProductService
"""
import os
import logging
import json
from decimal import Decimal
from unittest import TestCase
from urllib.parse import quote_plus
from service import app
from service.common import status
from service.models import db, init_db, Product
from tests.factories import ProductFactory
# Disable all but critical errors during normal test run
# uncomment for debugging failing tests
# logging.disable(logging.CRITICAL)

# DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///../db/test.db')
DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)
BASE_URL = "/products"


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductRoutes(TestCase):
    """Product Service tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        # Set up the test database
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        db.session.remove()

    ############################################################
    # Utility function to bulk create products
    ############################################################
    def _create_products(self, count: int = 1) -> list:
        """Factory method to create products in bulk"""
        products = []
        for _ in range(count):
            test_product = ProductFactory()
            response = self.client.post(BASE_URL, json=test_product.serialize())
            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, "Could not create test product"
            )
            new_product = response.get_json()
            test_product.id = new_product["id"]
            products.append(test_product)
        return products

    ############################################################
    #  T E S T   C A S E S
    ############################################################
    def test_index(self):
        """It should return the index page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b"Product Catalog Administration", response.data)

    def test_health(self):
        """It should be healthy"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data['message'], 'OK')

    # ----------------------------------------------------------
    # TEST CREATE
    # ----------------------------------------------------------
    def test_create_product(self):
        """It should Create a new Product"""
        test_product = ProductFactory()
        logging.debug("Test Product: %s", test_product.serialize())
        response = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

        # # Check that the location header was correct
        response = self.client.get(location)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

    def test_create_product_with_no_name(self):
        """It should not Create a Product without a name"""
        product = self._create_products()[0]
        new_product = product.serialize()
        del new_product["name"]
        logging.debug("Product no name: %s", new_product)
        response = self.client.post(BASE_URL, json=new_product)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_product_no_content_type(self):
        """It should not Create a Product with no Content-Type"""
        response = self.client.post(BASE_URL, data="bad data")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_product_wrong_content_type(self):
        """It should not Create a Product with wrong Content-Type"""
        response = self.client.post(BASE_URL, data={}, content_type="plain/text")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_get_product(self):
        """It should Get a single Product"""
        test_product = self._create_products(1)[0]
        logging.debug("Creating Test Product: %s", test_product.serialize())
        response = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["name"], test_product.name)

    def test_get_product_not_found(self):
        """It should not Get a Product thats not found"""
        response = self.client.get(f"{BASE_URL}/0")
        data = response.get_json()
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("was not found", data["message"])

    def test_update_product(self):
        """It should Update an existing Product"""
        # Create initial product
        test_product = self._create_products(1)[0]
        logging.debug("Creating Test Product: %s", test_product.serialize())
        response = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["name"], test_product.name)

        # Update the product
        test_product.name = "FooBar"
        logging.debug("Updating Product: %s", test_product.serialize())
        response = self.client.put(f"{BASE_URL}/{test_product.id}", json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert that attributes were updated
        response = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["name"], "FooBar")

    def test_update_product_not_found(self):
        """It should not Update non-existing Product"""
        test_product = ProductFactory()
        response = self.client.put(f"{BASE_URL}/0", json=test_product.serialize())
        data = response.get_json()
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("was not found", data["message"])

    def test_delete_product(self):
        """It should Delete a Product"""
        # Create initial products and check first
        test_product = self._create_products(5)[0]
        product_count = self.get_product_count()
        logging.debug("Creating Test Products: %s", test_product.serialize())
        response = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["name"], test_product.name)

        # Delete a product
        logging.debug("Deleting Product: %s", test_product.serialize())
        response = self.client.delete(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Assert that the Product was deleted
        response = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Assert that count of products changed
        new_count = self.get_product_count()
        self.assertEqual(new_count, product_count-1)

    def test_delete_product_not_found(self):
        """It should not Delete a Product if it doesn`t exist in the db"""
        # Delete a product
        logging.debug("Deleting non-existing Product with id 0")
        response = self.client.delete(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_all_products(self):
        """It should Get a list of Products"""
        # Creating batch of 10 products
        logging.debug("Creating batch of 10 test Products")
        products = self._create_products(10)

        # Checking list all products from API
        logging.debug("Requesting all products from API")
        response = self.client.get(f"{BASE_URL}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        logging.debug("Response from API: %s", response.data)
        data = response.get_json()
        self.assertEqual(len(data), 10)

        for product in products:
            self.assertIn(f"\"name\": \"{product.name}\"", json.dumps(data))

    def test_get_all_products_empty(self):
        """It should return empty list of Products and valid response on empty db"""
        # Checking list all products from API
        logging.debug("Requesting all products from API")
        response = self.client.get(f"{BASE_URL}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json(), [])

    def test_get_products_by_a_name(self):
        """It should Query Products by name"""
        # Creating batch of 5 products
        logging.debug("Creating batch of 5 test Products")
        products = self._create_products(5)

        # calculating required fields
        req_name = products[0].name
        req_count = 0
        for product in products:
            if product.name == req_name:
                req_count += 1

        # Requesting list of all products from API
        logging.debug("Requesting products from API with name %s", req_name)
        response = self.client.get(BASE_URL, query_string=f"name={quote_plus(req_name)}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        logging.debug("Response from API: %s", response.data)

        data = response.get_json()
        self.assertEqual(len(data), req_count)

    def test_get_products_by_a_category(self):
        """It should Query Products by category"""
        # Creating batch of 5 products
        logging.debug("Creating batch of 5 test Products")
        products = self._create_products(5)

        # calculating required fields
        req_category = products[0].category
        req_count = 0
        for product in products:
            if product.category == req_category:
                req_count += 1

        # Requesting list of all products from API
        logging.debug("Requesting products from API with category %s", req_category.name)
        response = self.client.get(BASE_URL, query_string=f"category={quote_plus(req_category.name)}")

        logging.debug("Response from API: %s", response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.get_json()
        self.assertEqual(len(data), req_count)

    def test_get_products_by_availability(self):
        """It should Query Products by availability"""
        # Creating batch of 5 products
        logging.debug("Creating batch of 5 test Products")
        products = self._create_products(5)

        # calculating required fields
        req_available = products[0].available
        req_count = 0
        for product in products:
            if product.available == req_available:
                req_count += 1

        # Requesting list of all products from API
        logging.debug("Requesting products from API with availability %s", req_available)

        response = self.client.get(BASE_URL, query_string=f"available={quote_plus(str(req_available))}")

        logging.debug("Response from API: %s", response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.get_json()
        self.assertEqual(len(data), req_count)

    ######################################################################
    # Utility functions
    ######################################################################

    def get_product_count(self):
        """save the current number of products"""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        # logging.debug("data = %s", data)
        return len(data)
