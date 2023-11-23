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

"""
Test cases for Product Model

Test cases can be run with:
    nosetests
    coverage report -m

While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_models.py:TestProductModel

"""
import os
import sys
import logging
import unittest
from unittest.mock import patch
from decimal import Decimal
from service.models import Product, Category, db, DataValidationError
from service import app
from tests.factories import ProductFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)


######################################################################
#  P R O D U C T   M O D E L   T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductModel(unittest.TestCase):
    """Test Cases for Product Model"""

    @classmethod
    def setUpClass(cls):
        """This runs once before the entire test suite"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        Product.init_db(app)

        # logger for tests
        cls.tstlogger = logging.getLogger("test_models")
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        cls.tstlogger.addHandler(handler)
        cls.tstlogger.setLevel(logging.CRITICAL)

    @classmethod
    def tearDownClass(cls):
        """This runs once after the entire test suite"""
        db.session.close()

    def setUp(self):
        """This runs before each test"""
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    ######################################################################
    #  T E S T   C A S E S
    ######################################################################

    def test_create_a_product(self):
        """It should Create a product and assert that it exists"""
        product = Product(name="Fedora", description="A red hat", price=12.50, available=True, category=Category.CLOTHS)
        self.assertEqual(str(product), "<Product Fedora id=[None]>")
        self.assertTrue(product is not None)
        self.assertEqual(product.id, None)
        self.assertEqual(product.name, "Fedora")
        self.assertEqual(product.description, "A red hat")
        self.assertEqual(product.available, True)
        self.assertEqual(product.price, 12.50)
        self.assertEqual(product.category, Category.CLOTHS)

    def test_invalid_deserialize_of_a_product(self):
        """ It should assert that exception is thrown for serialization / deserialization with incorrect data"""

        random_product = ProductFactory()
        good_product_data = random_product.serialize()

        # Assert that it is unable to get dict from empty Product
        with self.assertRaises(AttributeError):
            empty_product = Product()
            empty_product.serialize()

        # Assert that it is unable to create Product with incorrect 'available' boolean attribute
        incorrect_product_data = good_product_data
        incorrect_product_data["available"] = "FooBar"
        with self.assertRaises(DataValidationError):
            product = Product()
            product.deserialize(incorrect_product_data)

        # Assert that it is unable to create Product with incorrect input type
        with self.assertRaises(DataValidationError):
            product = Product()
            product.deserialize("random string incorrect input type")

        # Assert others deserialization exceptions
        with patch('service.models.getattr', side_effect=AttributeError):
            with self.assertRaises(IndexError):
                product = Product()
                product.deserialize(random_product.serialize())

        with patch('service.models.getattr', side_effect=KeyError):
            with self.assertRaises(IndexError):
                product = Product()
                product.deserialize(random_product.serialize())

        with patch('service.models.getattr', side_effect=TypeError):
            with self.assertRaises(DataValidationError):
                product = Product()
                product.deserialize(random_product.serialize())

    def test_add_a_product(self):
        """It should Create a Product and add it to the database"""
        products = Product.all()
        self.assertEqual(products, [])
        product = ProductFactory()
        product.id = None
        product.create()
        # Assert that it was assigned an id and shows up in the database
        self.assertIsNotNone(product.id)
        products = Product.all()
        self.assertEqual(len(products), 1)
        # Check that it matches the original product
        new_product = products[0]
        self.assertEqual(new_product.name, product.name)
        self.assertEqual(new_product.description, product.description)
        self.assertEqual(Decimal(new_product.price), product.price)
        self.assertEqual(new_product.available, product.available)
        self.assertEqual(new_product.category, product.category)

    def test_read_a_product(self):
        """It should Read a Product and assert that properties of the read product are correct"""
        product = ProductFactory()
        self.tstlogger.info("New product: %s", product)
        product.id = None
        product.create()
        self.assertIsNotNone(product.id)
        read_product = Product.find(product.id)
        self.tstlogger.info("Read product: %s", product)
        self.assertEqual(read_product.id, product.id)
        self.assertEqual(read_product.name, product.name)
        self.assertEqual(read_product.description, product.description)
        self.assertEqual(read_product.price, product.price)
        self.assertEqual(read_product.available, product.available)
        self.assertEqual(read_product.category, product.category)

    def test_update_a_product(self):
        """It should Update a Product and assert that fetched product has original id but updated description"""

        # Create a new product
        product = ProductFactory()
        self.tstlogger.info("New product: %s", product)
        product.id = None
        product.create()
        self.tstlogger.info("Created product: %s", product)
        self.assertIsNotNone(product.id)

        # Update the description property
        original_product_id = product.id
        original_product_description = product.description
        updated_product_description = "Foo Bar"
        product.description = updated_product_description
        product.update()
        self.tstlogger.info("Updated product: %s", product)
        # Assert that that the id and description properties of the product object have been updated correctly.
        self.assertEqual(product.id, original_product_id)
        self.assertEqual(product.description, updated_product_description)

        # Assert there is only 1 product in the DB
        all_products = Product.all()
        self.assertEqual(len(all_products), 1)
        self.tstlogger.info("Read product: %s", all_products[0])

        # Assert that a product has the original id but updated description.
        self.assertEqual(all_products[0].id, original_product_id)
        self.assertNotEqual(all_products[0].description, original_product_description)

    def test_update_an_empty_product(self):
        """It should Update a Product with empty id and check exception raised"""

        # Create a new product
        product = ProductFactory()
        self.tstlogger.info("New product: %s", product)
        product.id = None
        product.create()
        self.tstlogger.info("Created product: %s", product)
        self.assertIsNotNone(product.id)

        # Clearing id attribute and trying to update record in the db
        product.description = "Foo Bar Text"
        product.id = None
        with self.assertRaises(DataValidationError):
            product.update()

    def test_delete_a_product(self):
        """It should Delete a Product and assert that no records exists in the database"""

        # Create a new product
        product = ProductFactory()
        self.tstlogger.info("New product: %s", product)
        product.id = None
        product.create()
        self.tstlogger.info("Created product: %s", product)
        self.assertIsNotNone(product.id)

        # Assert there is only 1 product in the DB
        self.assertEqual(len(Product.all()), 1)

        # Delete a product and assert the is no records in the DB
        product.delete()
        self.tstlogger.info("Deleted product: %s", product)
        self.assertEqual(len(Product.all()), 0)

    def test_list_all_products(self):
        """It should List all Products in the databases"""

        # Assert the is no records in the DB
        self.assertEqual(len(Product.all()), 0)

        # Create new products
        products = ProductFactory.create_batch(5)
        for product in products:
            product.create()

        # Assert there are 5 products in the DB
        self.assertEqual(len(Product.all()), 5)

    def test_find_a_product_by_a_name(self):
        """It should Find a Products by Name"""

        # Assert the is no records in the DB
        self.assertEqual(len(Product.all()), 0)

        # Create new products
        products = ProductFactory.create_batch(5)
        for product in products:
            product.create()
            self.tstlogger.info("Created product: %s", product)

        # Assert there are 5 products in the DB
        self.assertEqual(len(Product.all()), 5)

        # Assert that find_by_name find all products with given name
        req_name = products[0].name
        req_count = 0
        for product in products:
            if req_name == product.name:
                req_count += 1

        found_products = Product.find_by_name(req_name)
        self.assertEqual(found_products.count(), req_count)

        # Assert that names from products selected by find_by_name are correct
        for found_product in found_products:
            self.tstlogger.info("Found product: %s", found_product)
            self.assertEqual(found_product.name, req_name)

    def test_find_a_product_by_availability(self):
        """It should Find Products by Availability"""

        # Assert the is no records in the DB
        self.assertEqual(len(Product.all()), 0)

        # Create new products
        products = ProductFactory.create_batch(10)
        for product in products:
            product.create()
            self.tstlogger.info("Created product: %s, available: %s", product, product.available)

        # Assert there are 10 products in the DB
        self.assertEqual(len(Product.all()), 10)

        # Assert that find_by_availability finds required products
        req_availability = products[0].available
        req_count = 0
        for product in products:
            if req_availability == product.available:
                req_count += 1

        found_products = Product.find_by_availability(req_availability)
        self.assertEqual(found_products.count(), req_count)

        # Assert that availabilitu of each found element is correct
        for found_product in found_products:
            self.tstlogger.info("Found product: %s, available: %s", found_product, found_product.available)
            self.assertEqual(found_product.available, req_availability)

    def test_find_a_product_by_a_category(self):
        """It should Find Products by Category"""

        # Assert the is no records in the DB
        self.assertEqual(len(Product.all()), 0)

        # Create new products
        products = ProductFactory.create_batch(10)
        for product in products:
            product.create()
            self.tstlogger.info("Created product: %s, category: %s", product, product.category)

        # Assert there are 10 products in the DB
        self.assertEqual(len(Product.all()), 10)

        # Assert that find_by_availability finds required products
        req_category = products[0].category
        req_count = 0
        for product in products:
            if req_category == product.category:
                req_count += 1

        found_products = Product.find_by_category(req_category)
        self.assertEqual(found_products.count(), req_count)

        # Assert that availabilitu of each found element is correct
        for found_product in found_products:
            self.tstlogger.info("Found product: %s, category: %s", found_product, found_product.category)
            self.assertEqual(found_product.category, req_category)

    def test_find_a_product_by_a_price(self):
        """It should Find Products by Price"""

        # Assert the is no records in the DB
        self.assertEqual(len(Product.all()), 0)

        # Create new products
        products = ProductFactory.create_batch(10)
        for product in products:
            product.create()
            self.tstlogger.info("Created product: %s, price: %s", product, product.price)

        # Assert there are 10 products in the DB
        self.assertEqual(len(Product.all()), 10)

        # Assert that find_by_price finds required products
        req_price = products[0].price
        req_count = 0
        for product in products:
            if req_price == product.price:
                req_count += 1

        # Assert find by price (Decimal)
        found_products = Product.find_by_price(req_price)
        self.assertEqual(found_products.count(), req_count)
        # Assert that availabilitu of each found element is correct
        for found_product in found_products:
            self.tstlogger.info("Found product: %s, price: %s", found_product, found_product.price)
            self.assertEqual(found_product.price, req_price)

        # Assert find by price (str)
        found_products = Product.find_by_price(str(req_price))
        self.assertEqual(found_products.count(), req_count)
        for found_product in found_products:
            self.tstlogger.info("Found product: %s, price: %s", found_product, found_product.price)
            self.assertEqual(found_product.price, req_price)
