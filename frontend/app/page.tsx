"use client";

import { useEffect, useState, useRef } from "react";
import axios from "axios";

// --- Typy ---

interface Category {
  id: number;
  name: string;
  description?: string;
}

interface Product {
  id: number;
  name: string;
  description?: string;
  price: number;
  quantity: number;
  low_stock_threshold: number;
  category_id?: number;
  category?: Category;
}

interface ServerStatus {
  timestamp: string;
  status: string;
  connected_clients: number;
}

interface Alert {
  product: string;
  message: string;
}

// --- Konfiguracja ---
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";

export default function Home() {
  // --- Stan aplikacji ---
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [serverStatus, setServerStatus] = useState<ServerStatus | null>(null);
  const [alert, setAlert] = useState<Alert | null>(null);
  const [activeTab, setActiveTab] = useState<"products" | "categories">(
    "products"
  );

  // Stan formularza produktu
  const [isEditing, setIsEditing] = useState(false);
  const [currentId, setCurrentId] = useState<number | null>(null);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    price: "",
    quantity: "",
    low_stock_threshold: "5",
    category_id: "",
  });

  // Stan formularza kategorii
  const [isEditingCategory, setIsEditingCategory] = useState(false);
  const [currentCategoryId, setCurrentCategoryId] = useState<number | null>(
    null
  );
  const [categoryFormData, setCategoryFormData] = useState({
    name: "",
    description: "",
  });

  const ws = useRef<WebSocket | null>(null);

  // --- Efekty ---

  // 1. Pobranie produktow i kategorii przy montowaniu komponentu
  useEffect(() => {
    fetchProducts();
    fetchCategories();
  }, []);

  // 2. Polaczenie WebSocket z automatycznym reconnect
  useEffect(() => {
    let reconnectTimeout: NodeJS.Timeout;
    let isUnmounted = false;

    const connect = () => {
      if (isUnmounted) return;

      ws.current = new WebSocket(WS_URL);

      ws.current.onopen = () => {
        console.log("Connected to WebSocket");
      };

      ws.current.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === "status") {
          setServerStatus({
            timestamp: data.timestamp,
            status: data.status,
            connected_clients: data.connected_clients,
          });
        } else if (data.type === "alert") {
          setAlert({
            product: data.product,
            message: data.message,
          });
          // Automatyczne ukrycie alertu po 10 sekundach
          setTimeout(() => setAlert(null), 10000);
        } else if (data.type === "product_created") {
          setProducts((prev) => [...prev, data.product]);
        } else if (data.type === "product_updated") {
          setProducts((prev) =>
            prev.map((p) => (p.id === data.product.id ? data.product : p))
          );
        } else if (data.type === "product_deleted") {
          setProducts((prev) => prev.filter((p) => p.id !== data.product_id));
        } else if (data.type === "category_created") {
          setCategories((prev) => [...prev, data.category]);
        } else if (data.type === "category_updated") {
          setCategories((prev) =>
            prev.map((c) => (c.id === data.category.id ? data.category : c))
          );
        } else if (data.type === "category_deleted") {
          setCategories((prev) =>
            prev.filter((c) => c.id !== data.category_id)
          );
          // Aktualizacja produktow - usuniecie przypisania kategorii
          setProducts((prev) =>
            prev.map((p) =>
              p.category_id === data.category_id
                ? { ...p, category_id: undefined, category: undefined }
                : p
            )
          );
        }
      };

      ws.current.onclose = () => {
        console.log("Disconnected from WebSocket, reconnecting in 3s...");
        if (!isUnmounted) {
          reconnectTimeout = setTimeout(connect, 3000);
        }
      };

      ws.current.onerror = () => {
        console.log("WebSocket error, closing...");
        ws.current?.close();
      };
    };

    connect();

    return () => {
      isUnmounted = true;
      clearTimeout(reconnectTimeout);
      ws.current?.close();
    };
  }, []);

  // --- Funkcje API ---

  const fetchProducts = async () => {
    try {
      const response = await axios.get(`${API_URL}/products/`);
      setProducts(response.data);
    } catch (error) {
      console.error("Error fetching products:", error);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await axios.get(`${API_URL}/categories/`);
      setCategories(response.data);
    } catch (error) {
      console.error("Error fetching categories:", error);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Czy na pewno chcesz usunac ten produkt?")) return;
    try {
      await axios.delete(`${API_URL}/products/${id}`);
    } catch (error) {
      console.error("Error deleting product:", error);
    }
  };

  const handleDeleteCategory = async (id: number) => {
    if (
      !confirm(
        "Czy na pewno chcesz usunac te kategorie? Produkty przypisane do tej kategorii zostana odpiete."
      )
    )
      return;
    try {
      await axios.delete(`${API_URL}/categories/${id}`);
    } catch (error) {
      console.error("Error deleting category:", error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      ...formData,
      price: parseFloat(formData.price) || 0,
      quantity: parseInt(formData.quantity) || 0,
      low_stock_threshold: parseInt(formData.low_stock_threshold) || 0,
      category_id: formData.category_id ? parseInt(formData.category_id) : null,
    };

    try {
      if (isEditing && currentId) {
        await axios.put(`${API_URL}/products/${currentId}`, payload);
      } else {
        await axios.post(`${API_URL}/products/`, payload);
      }
      // Resetowanie formularza
      setFormData({
        name: "",
        description: "",
        price: "",
        quantity: "",
        low_stock_threshold: "5",
        category_id: "",
      });
      setIsEditing(false);
      setCurrentId(null);
    } catch (error) {
      console.error("Error saving product:", error);
    }
  };

  const handleCategorySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      name: categoryFormData.name,
      description: categoryFormData.description || null,
    };

    try {
      if (isEditingCategory && currentCategoryId) {
        await axios.put(`${API_URL}/categories/${currentCategoryId}`, payload);
      } else {
        await axios.post(`${API_URL}/categories/`, payload);
      }
      // Resetowanie formularza
      setCategoryFormData({
        name: "",
        description: "",
      });
      setIsEditingCategory(false);
      setCurrentCategoryId(null);
    } catch (error) {
      console.error("Error saving category:", error);
    }
  };

  const startEdit = (product: Product) => {
    setIsEditing(true);
    setCurrentId(product.id);
    setFormData({
      name: product.name,
      description: product.description || "",
      price: product.price.toString(),
      quantity: product.quantity.toString(),
      low_stock_threshold: product.low_stock_threshold.toString(),
      category_id: product.category_id?.toString() || "",
    });
  };

  const startEditCategory = (category: Category) => {
    setIsEditingCategory(true);
    setCurrentCategoryId(category.id);
    setCategoryFormData({
      name: category.name,
      description: category.description || "",
    });
  };

  // --- Renderowanie ---

  return (
    <div className="min-h-screen bg-gray-100 p-8 font-sans text-gray-900">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Naglowek i Status Serwera */}
        <header className="flex justify-between items-center bg-white p-6 rounded-lg shadow-md">
          <div>
            <h1 className="text-3xl font-bold text-blue-600">StockGuard</h1>
            <p className="text-gray-500">
              System Zarzadzania Magazynem (Tryb Kiosk)
            </p>
          </div>
          <div className="text-right">
            <div className="text-sm font-semibold text-gray-600">
              Status Serwera
            </div>
            <div className="flex items-center gap-2 justify-end">
              <span
                className={`h-3 w-3 rounded-full ${
                  serverStatus ? "bg-green-500" : "bg-red-500"
                }`}
              ></span>
              <span>{serverStatus ? serverStatus.status : "Niedostepny"}</span>
            </div>
            <div className="text-xs text-gray-400 font-mono">
              {serverStatus
                ? new Date(serverStatus.timestamp).toLocaleString()
                : "--:--:--"}
            </div>
            <div className="text-xs text-gray-500">
              Podlaczonych klientow: {serverStatus?.connected_clients ?? 0}
            </div>
          </div>
        </header>

        {/* Baner Alertow */}
        {alert && (
          <div
            className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 rounded shadow-lg animate-pulse"
            role="alert"
          >
            <p className="font-bold">⚠️ Alert: Niski Stan Magazynowy!</p>
            <p>{alert.message}</p>
          </div>
        )}

        {/* Zakladki */}
        <div className="flex gap-4 border-b border-gray-300">
          <button
            onClick={() => setActiveTab("products")}
            className={`py-2 px-4 font-semibold ${
              activeTab === "products"
                ? "border-b-2 border-blue-600 text-blue-600"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            Produkty
          </button>
          <button
            onClick={() => setActiveTab("categories")}
            className={`py-2 px-4 font-semibold ${
              activeTab === "categories"
                ? "border-b-2 border-blue-600 text-blue-600"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            Kategorie
          </button>
        </div>

        {activeTab === "products" ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Formularz Produktu */}
            <div className="lg:col-span-1">
              <div className="bg-white p-6 rounded-lg shadow-md">
                <h2 className="text-xl font-semibold mb-4 border-b pb-2">
                  {isEditing ? "Edytuj Produkt" : "Dodaj Nowy Produkt"}
                </h2>
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Nazwa
                    </label>
                    <input
                      type="text"
                      required
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border"
                      value={formData.name}
                      onChange={(e) =>
                        setFormData({ ...formData, name: e.target.value })
                      }
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Opis
                    </label>
                    <textarea
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border"
                      value={formData.description}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          description: e.target.value,
                        })
                      }
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Kategoria
                    </label>
                    <select
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border"
                      value={formData.category_id}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          category_id: e.target.value,
                        })
                      }
                    >
                      <option value="">-- Brak kategorii --</option>
                      {categories.map((cat) => (
                        <option key={cat.id} value={cat.id}>
                          {cat.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        Cena
                      </label>
                      <input
                        type="number"
                        step="0.01"
                        required
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border"
                        value={formData.price}
                        onChange={(e) =>
                          setFormData({ ...formData, price: e.target.value })
                        }
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        Ilosc
                      </label>
                      <input
                        type="number"
                        required
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border"
                        value={formData.quantity}
                        onChange={(e) =>
                          setFormData({ ...formData, quantity: e.target.value })
                        }
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Prog Niskiego Stanu
                    </label>
                    <input
                      type="number"
                      required
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border"
                      value={formData.low_stock_threshold}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          low_stock_threshold: e.target.value,
                        })
                      }
                    />
                  </div>
                  <div className="flex gap-2 pt-2">
                    <button
                      type="submit"
                      className="flex-1 bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 transition-colors"
                    >
                      {isEditing ? "Zapisz" : "Dodaj"}
                    </button>
                    {isEditing && (
                      <button
                        type="button"
                        onClick={() => {
                          setIsEditing(false);
                          setFormData({
                            name: "",
                            description: "",
                            price: "",
                            quantity: "",
                            low_stock_threshold: "5",
                            category_id: "",
                          });
                        }}
                        className="bg-gray-300 text-gray-700 py-2 px-4 rounded hover:bg-gray-400 transition-colors"
                      >
                        Anuluj
                      </button>
                    )}
                  </div>
                </form>
              </div>
            </div>

            {/* Lista Produktow */}
            <div className="lg:col-span-2">
              <div className="bg-white rounded-lg shadow-md overflow-hidden">
                <div className="p-6 border-b">
                  <h2 className="text-xl font-semibold">Magazyn</h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Nazwa
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Kategoria
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Cena
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Ilosc
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Status
                        </th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Akcje
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {products.map((product) => (
                        <tr key={product.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm font-medium text-gray-900">
                              {product.name}
                            </div>
                            <div className="text-sm text-gray-500 truncate max-w-xs">
                              {product.description}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {product.category?.name || "-"}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            ${product.price.toFixed(2)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {product.quantity}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            {product.quantity < product.low_stock_threshold ? (
                              <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800">
                                Niski Stan
                              </span>
                            ) : (
                              <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                                OK
                              </span>
                            )}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                            <button
                              onClick={() => startEdit(product)}
                              className="text-indigo-600 hover:text-indigo-900 mr-4"
                            >
                              Edytuj
                            </button>
                            <button
                              onClick={() => handleDelete(product.id)}
                              className="text-red-600 hover:text-red-900"
                            >
                              Usun
                            </button>
                          </td>
                        </tr>
                      ))}
                      {products.length === 0 && (
                        <tr>
                          <td
                            colSpan={6}
                            className="px-6 py-4 text-center text-gray-500"
                          >
                            Brak produktow. Dodaj pierwszy produkt.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Formularz Kategorii */}
            <div className="lg:col-span-1">
              <div className="bg-white p-6 rounded-lg shadow-md">
                <h2 className="text-xl font-semibold mb-4 border-b pb-2">
                  {isEditingCategory
                    ? "Edytuj Kategorie"
                    : "Dodaj Nowa Kategorie"}
                </h2>
                <form onSubmit={handleCategorySubmit} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Nazwa
                    </label>
                    <input
                      type="text"
                      required
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border"
                      value={categoryFormData.name}
                      onChange={(e) =>
                        setCategoryFormData({
                          ...categoryFormData,
                          name: e.target.value,
                        })
                      }
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Opis
                    </label>
                    <textarea
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border"
                      value={categoryFormData.description}
                      onChange={(e) =>
                        setCategoryFormData({
                          ...categoryFormData,
                          description: e.target.value,
                        })
                      }
                    />
                  </div>
                  <div className="flex gap-2 pt-2">
                    <button
                      type="submit"
                      className="flex-1 bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 transition-colors"
                    >
                      {isEditingCategory ? "Zapisz" : "Dodaj"}
                    </button>
                    {isEditingCategory && (
                      <button
                        type="button"
                        onClick={() => {
                          setIsEditingCategory(false);
                          setCategoryFormData({
                            name: "",
                            description: "",
                          });
                        }}
                        className="bg-gray-300 text-gray-700 py-2 px-4 rounded hover:bg-gray-400 transition-colors"
                      >
                        Anuluj
                      </button>
                    )}
                  </div>
                </form>
              </div>
            </div>

            {/* Lista Kategorii */}
            <div className="lg:col-span-2">
              <div className="bg-white rounded-lg shadow-md overflow-hidden">
                <div className="p-6 border-b">
                  <h2 className="text-xl font-semibold">Kategorie</h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          ID
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Nazwa
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Opis
                        </th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Akcje
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {categories.map((category) => (
                        <tr key={category.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {category.id}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm font-medium text-gray-900">
                              {category.name}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {category.description || "-"}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                            <button
                              onClick={() => startEditCategory(category)}
                              className="text-indigo-600 hover:text-indigo-900 mr-4"
                            >
                              Edytuj
                            </button>
                            <button
                              onClick={() => handleDeleteCategory(category.id)}
                              className="text-red-600 hover:text-red-900"
                            >
                              Usun
                            </button>
                          </td>
                        </tr>
                      ))}
                      {categories.length === 0 && (
                        <tr>
                          <td
                            colSpan={4}
                            className="px-6 py-4 text-center text-gray-500"
                          >
                            Brak kategorii. Dodaj pierwsza kategorie.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
