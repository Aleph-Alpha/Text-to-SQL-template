CREATE TABLE Categories (
    CategoryID    INTEGER,
    PRIMARY KEY (CategoryID),
    CategoryName  TEXT,
    Description   TEXT,
    Picture       BLOB   
);
CREATE TABLE CustomerCustomerDemo (
    CustomerID      TEXT  NOT NULL,
    CustomerTypeID  TEXT  NOT NULL,
    CONSTRAINT sqlite_autoindex_CustomerCustomerDemo_1 UNIQUE (CustomerID, CustomerTypeID),
    FOREIGN KEY (CustomerTypeID) REFERENCES CustomerDemographics (CustomerTypeID),
    FOREIGN KEY (CustomerID) REFERENCES Customers (CustomerID),
    PRIMARY KEY (CustomerID, CustomerTypeID)
);
CREATE TABLE CustomerDemographics (
    CustomerTypeID  TEXT  NOT NULL,
    PRIMARY KEY (CustomerTypeID),
    CustomerDesc    TEXT,
    CONSTRAINT sqlite_autoindex_CustomerDemographics_1 UNIQUE (CustomerTypeID)
);
CREATE TABLE Customers (
    CustomerID    TEXT,
    PRIMARY KEY (CustomerID),
    CompanyName   TEXT,
    ContactName   TEXT,
    ContactTitle  TEXT,
    Address       TEXT,
    City          TEXT,
    Region        TEXT,
    PostalCode    TEXT,
    Country       TEXT,
    Phone         TEXT,
    Fax           TEXT,
    CONSTRAINT sqlite_autoindex_Customers_1 UNIQUE (CustomerID)
);
CREATE TABLE EmployeeTerritories (
    EmployeeID   INTEGER  NOT NULL,
    TerritoryID  TEXT     NOT NULL,
    CONSTRAINT sqlite_autoindex_EmployeeTerritories_1 UNIQUE (EmployeeID, TerritoryID),
    FOREIGN KEY (TerritoryID) REFERENCES Territories (TerritoryID),
    FOREIGN KEY (EmployeeID) REFERENCES Employees (EmployeeID),
    PRIMARY KEY (EmployeeID, TerritoryID)
);
CREATE TABLE Employees (
    EmployeeID       INTEGER,
    PRIMARY KEY (EmployeeID),
    LastName         TEXT,
    FirstName        TEXT,
    Title            TEXT,
    TitleOfCourtesy  TEXT,
    BirthDate        DATE,
    HireDate         DATE,
    Address          TEXT,
    City             TEXT,
    Region           TEXT,
    PostalCode       TEXT,
    Country          TEXT,
    HomePhone        TEXT,
    Extension        TEXT,
    Photo            BLOB,
    Notes            TEXT,
    ReportsTo        INTEGER,
    PhotoPath        TEXT,
    FOREIGN KEY (ReportsTo) REFERENCES Employees (EmployeeID)
);
CREATE TABLE Order Details (
    OrderID    INTEGER  NOT NULL,
    ProductID  INTEGER  NOT NULL,
    UnitPrice  NUMERIC  NOT NULL  DEFAULT 0,
    Quantity   INTEGER  NOT NULL  DEFAULT 1,
    Discount   REAL     NOT NULL  DEFAULT 0,
    CONSTRAINT sqlite_autoindex_Order Details_1 UNIQUE (OrderID, ProductID),
    FOREIGN KEY (ProductID) REFERENCES Products (ProductID),
    FOREIGN KEY (OrderID) REFERENCES Orders (OrderID),
    PRIMARY KEY (OrderID, ProductID)
);
CREATE TABLE Orders (
    OrderID         INTEGER   NOT NULL,
    PRIMARY KEY (OrderID),
    CustomerID      TEXT,
    EmployeeID      INTEGER,
    OrderDate       DATETIME,
    RequiredDate    DATETIME,
    ShippedDate     DATETIME,
    ShipVia         INTEGER,
    Freight         NUMERIC   DEFAULT 0,
    ShipName        TEXT,
    ShipAddress     TEXT,
    ShipCity        TEXT,
    ShipRegion      TEXT,
    ShipPostalCode  TEXT,
    ShipCountry     TEXT,
    FOREIGN KEY (ShipVia) REFERENCES Shippers (ShipperID),
    FOREIGN KEY (CustomerID) REFERENCES Customers (CustomerID),
    FOREIGN KEY (EmployeeID) REFERENCES Employees (EmployeeID)
);
CREATE TABLE Products (
    ProductID        INTEGER  NOT NULL,
    PRIMARY KEY (ProductID),
    ProductName      TEXT     NOT NULL,
    SupplierID       INTEGER,
    CategoryID       INTEGER,
    QuantityPerUnit  TEXT,
    UnitPrice        NUMERIC  DEFAULT 0,
    UnitsInStock     INTEGER  DEFAULT 0,
    UnitsOnOrder     INTEGER  DEFAULT 0,
    ReorderLevel     INTEGER  DEFAULT 0,
    Discontinued     TEXT     NOT NULL  DEFAULT '0',
    FOREIGN KEY (SupplierID) REFERENCES Suppliers (SupplierID),
    FOREIGN KEY (CategoryID) REFERENCES Categories (CategoryID)
);
CREATE TABLE Regions (
    RegionID           INTEGER  NOT NULL,
    PRIMARY KEY (RegionID),
    RegionDescription  TEXT     NOT NULL
);
CREATE TABLE Shippers (
    ShipperID    INTEGER  NOT NULL,
    PRIMARY KEY (ShipperID),
    CompanyName  TEXT     NOT NULL,
    Phone        TEXT   
);
CREATE TABLE Suppliers (
    SupplierID    INTEGER  NOT NULL,
    PRIMARY KEY (SupplierID),
    CompanyName   TEXT     NOT NULL,
    ContactName   TEXT,
    ContactTitle  TEXT,
    Address       TEXT,
    City          TEXT,
    Region        TEXT,
    PostalCode    TEXT,
    Country       TEXT,
    Phone         TEXT,
    Fax           TEXT,
    HomePage      TEXT   
);
CREATE TABLE Territories (
    TerritoryID           TEXT     NOT NULL,
    PRIMARY KEY (TerritoryID),
    TerritoryDescription  TEXT     NOT NULL,
    RegionID              INTEGER  NOT NULL,
    CONSTRAINT sqlite_autoindex_Territories_1 UNIQUE (TerritoryID),
    FOREIGN KEY (RegionID) REFERENCES Regions (RegionID)
);
