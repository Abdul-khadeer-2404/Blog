import React, { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { Heart, Share2, Copy, Facebook, Twitter, Linkedin, Mail, X } from "lucide-react";
import { useAuth } from "../context/AuthContext";

interface Post {
  id: number;
  title: string;
  content: string;
  created_at: string;
  author: {
    username: string;
    profile_picture?: string; // Add this field to the interface
  };
  like_count: number;
  is_liked: boolean;
}

const Home = () => {
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [likingPosts, setLikingPosts] = useState<Set<number>>(new Set());
  const [shareDropdown, setShareDropdown] = useState<number | null>(null);
  const shareRef = useRef<HTMLDivElement>(null);
  const { user, token } = useAuth();

  useEffect(() => {
    fetchPosts();
  }, []);

  // Close share dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (shareRef.current && !shareRef.current.contains(event.target as Node)) {
        setShareDropdown(null);
      }
    };

    if (shareDropdown !== null) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [shareDropdown]);

  const handleShare = (postId: number, type: string, post: Post) => {
    const postUrl = `${window.location.origin}/post/${postId}`;
    const shareText = `Check out this post: "${post.title}" by ${post.author.username}`;
    
    switch (type) {
      case 'copy':
        navigator.clipboard.writeText(postUrl).then(() => {
          alert('Link copied to clipboard!');
          setShareDropdown(null);
        }).catch(() => {
          alert('Failed to copy link');
        });
        break;
        
      case 'twitter':
        const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(postUrl)}`;
        window.open(twitterUrl, '_blank');
        setShareDropdown(null);
        break;
        
      case 'facebook':
        const facebookUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(postUrl)}`;
        window.open(facebookUrl, '_blank');
        setShareDropdown(null);
        break;
        
      case 'linkedin':
        const linkedinUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(postUrl)}`;
        window.open(linkedinUrl, '_blank');
        setShareDropdown(null);
        break;
        
      case 'email':
        const emailUrl = `mailto:?subject=${encodeURIComponent(post.title)}&body=${encodeURIComponent(shareText + '\n\n' + postUrl)}`;
        window.location.href = emailUrl;
        setShareDropdown(null);
        break;
        
      case 'native':
        if (navigator.share) {
          navigator.share({
            title: post.title,
            text: shareText,
            url: postUrl,
          }).then(() => {
            setShareDropdown(null);
          }).catch((error) => {
            console.log('Error sharing:', error);
          });
        }
        break;
        
      default:
        break;
    }
  };

  const toggleShareDropdown = (postId: number) => {
    setShareDropdown(shareDropdown === postId ? null : postId);
  };

  const fetchPosts = async () => {
    try {
      setLoading(true);
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      
      // Add authorization header if user is logged in
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch("http://localhost:5000/api/posts", {
        headers
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || "Failed to fetch posts");
      }

      setPosts(Array.isArray(data) ? data : []);
    } catch (err: any) {
      console.error("Error fetching posts:", err);
      setError(err.message || "Failed to fetch posts");
    } finally {
      setLoading(false);
    }
  };

  // Fixed function to get profile picture for each post author
  const getProfilePictureUrl = (authorUsername: string, profilePicture?: string) => {
    if (!profilePicture) {
      return `https://ui-avatars.com/api/?name=${authorUsername}&background=random`;
    }
    return `http://localhost:5000/uploads/${profilePicture}`;
  };

  const handleLike = async (postId: number) => {
    if (!user) {
      alert("Please log in to like posts");
      return;
    }

    if (likingPosts.has(postId)) {
      return; // Prevent multiple simultaneous requests
    }

    try {
      setLikingPosts(prev => {
        const newSet = new Set(prev);
        newSet.add(postId);
        return newSet;
      });
      
      if (!token) {
        alert("Please log in to like posts");
        return;
      }

      const response = await fetch(`http://localhost:5000/api/posts/${postId}/like`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || "Failed to toggle like");
      }

      // Update the specific post in the posts array
      setPosts(prevPosts => 
        prevPosts.map(post => 
          post.id === postId 
            ? { 
                ...post, 
                like_count: data.like_count,
                is_liked: data.is_liked 
              }
            : post
        )
      );

    } catch (err: any) {
      console.error("Error toggling like:", err);
      alert(err.message || "Failed to toggle like");
    } finally {
      setLikingPosts(prev => {
        const newSet = new Set(prev);
        newSet.delete(postId);
        return newSet;
      });
    }
  };

  const isShareSupported = typeof navigator !== 'undefined' && 'share' in navigator;

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="w-6 h-6 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-center">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-gray-900">Latest Posts</h1>
      </div>

      {posts.length === 0 ? (
        <div className="border border-gray-200 rounded-lg p-8 text-center">
          <p className="text-gray-500">
            No posts yet. {user && "Be the first to create one!"}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {posts.map((post) => (
            <article
              key={post.id}
              className="border border-gray-200 rounded-lg p-6 bg-white"
            >
              {/* Author section with profile picture and username */}
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center border">
                  <img
                    src={getProfilePictureUrl(post.author.username, post.author.profile_picture)}
                    alt={post.author.username}
                    className="w-9 h-9 rounded-full object-cover border border-gray-200"
                  />
                </div>
                <span className="text-sm font-medium text-gray-900">
                  {post.author.username}
                </span>
              </div>

              {/* Title */}
              <h2 className="text-lg font-semibold text-gray-900 mb-3">
                {post.title}
              </h2>

              {/* Content */}
              <div className="mb-4">
                <p className="text-gray-700 leading-relaxed">
                  {post.content.length > 150
                    ? `${post.content.substring(0, 150)}...`
                    : post.content}
                </p>
              </div>

              {/* Date and Icons */}
              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-500">
                  {new Date(post.created_at).toLocaleDateString("en-US", {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })}
                </div>
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleLike(post.id)}
                      disabled={likingPosts.has(post.id)}
                      className="disabled:cursor-not-allowed"
                    >
                      <Heart 
                        className={`w-4 h-4 cursor-pointer transition-colors ${
                          post.is_liked
                            ? 'text-red-500 fill-red-500' 
                            : 'text-gray-500 hover:text-red-500'
                        } ${likingPosts.has(post.id) ? 'opacity-50' : ''}`}
                      />
                    </button>
                    <span className="text-sm text-gray-500">
                      {post.like_count}
                    </span>
                  </div>
                  
                  {/* Share Button with Dropdown */}
                  <div className="relative" ref={shareRef}>
                    <button
                      onClick={() => toggleShareDropdown(post.id)}
                      className="flex items-center gap-1"
                    >
                      <Share2 className="w-4 h-4 text-gray-500 cursor-pointer hover:text-blue-500 transition-colors" />
                    </button>
                    
                    {/* Share Dropdown */}
                    {shareDropdown === post.id && (
                      <div className="absolute right-0 top-8 bg-white border border-gray-200 rounded-lg shadow-lg py-2 z-10 min-w-[200px]">
                        <div className="px-3 py-2 text-sm font-medium text-gray-700 border-b border-gray-100">
                          Share this post
                        </div>
                        
                        {/* Native Share (if supported) */}
                        {isShareSupported && (
                          <button
                            onClick={() => handleShare(post.id, 'native', post)}
                            className="w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                          >
                            <Share2 className="w-4 h-4" />
                            Share via...
                          </button>
                        )}
                        
                        <button
                          onClick={() => handleShare(post.id, 'copy', post)}
                          className="w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                        >
                          <Copy className="w-4 h-4" />
                          Copy link
                        </button>
                        
                        <button
                          onClick={() => handleShare(post.id, 'twitter', post)}
                          className="w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                        >
                          <Twitter className="w-4 h-4" />
                          Share on Twitter
                        </button>
                        
                        <button
                          onClick={() => handleShare(post.id, 'facebook', post)}
                          className="w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                        >
                          <Facebook className="w-4 h-4" />
                          Share on Facebook
                        </button>
                        
                        <button
                          onClick={() => handleShare(post.id, 'linkedin', post)}
                          className="w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                        >
                          <Linkedin className="w-4 h-4" />
                          Share on LinkedIn
                        </button>
                        
                        <button
                          onClick={() => handleShare(post.id, 'email', post)}
                          className="w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                        >
                          <Mail className="w-4 h-4" />
                          Share via Email
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
};

export default Home;